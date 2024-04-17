import ipaddress

from app.model.control_plane import ControlPlaneVm
from app.model.pve import PveNode
from app.error import *
from app import util
from app import config
from app.model.vm import Vm
from app.model.worker import WorkerVm


class WorkerService:

    def __init__(self, nodectl: PveNode) -> None:
        self.nodectl = nodectl
        pass

    def create_worker(self,
                      vm_network_name: str,
                      vm_template_id: int,
                      install_containerd_filepath: str,
                      install_kube_filepath: str,
                      containerd_config_filepath: str,
                      existed_control_plane_vm_id: int = None,
                      preserved_ips=[],
                      vm_id_range=config.PROXMOX_VM_ID_RANGE,
                      vm_core_count=4,
                      vm_memory=8192,
                      vm_disk_size="20G",
                      vm_name_prefix="i-",
                      vm_username="u",
                      vm_password="1",
                      vm_ssh_keys=None,
                      vm_start_on_boot=1,
                      **kwargs):
        nodectl = self.nodectl

        r = nodectl.describe_network(vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for ip in vm_network.hosts():
            ip_pool.append(str(ip))
        preserved_ips.append(network_gw_ip)
        util.log.debug("preserved_ips", preserved_ips)

        vm_list = nodectl.list_vm(vm_id_range)
        new_vm_id = nodectl.new_vm_id(vm_list, vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(vm_list, ip_pool, preserved_ips)
        new_vm_name = f"{vm_name_prefix}{new_vm_id}"

        util.log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        nodectl.clone(vm_template_id, new_vm_id)

        wkctl = WorkerVm(nodectl.api, nodectl.node, new_vm_id)
        wkctl.update_config(
            name=new_vm_name,
            cpu="cputype=host",
            cores=vm_core_count,
            memory=vm_memory,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.Proxmox.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
            onboot=vm_start_on_boot,
            tags=";".join([config.Tag.wk, config.Tag.kp]),
        )
        wkctl.resize_disk("scsi0", vm_disk_size)

        wkctl.startup()
        wkctl.wait_for_guest_agent()
        util.log.info("started vm", new_vm_id)

        wkctl.wait_for_cloud_init()
        util.log.info("waited for cloud-init", new_vm_id)

        vm_install_containerd_location = "/usr/local/bin/install-containerd.sh"
        with open(install_containerd_filepath, "r") as f:
            wkctl.write_file(vm_install_containerd_location, f.read())
        wkctl.exec(f"chmod +x {vm_install_containerd_location}")
        wkctl.exec(vm_install_containerd_location)

        with open(containerd_config_filepath) as f:
            wkctl.write_file("/etc/containerd/config.toml", f.read())
        wkctl.exec("systemctl restart containerd")

        vm_install_kube_location = "/usr/local/bin/install-kube.sh"
        with open(install_kube_filepath, "r") as f:
            wkctl.write_file(vm_install_kube_location, f.read())
        wkctl.exec(f"chmod +x {vm_install_kube_location}")
        wkctl.exec(vm_install_kube_location)

        if not existed_control_plane_vm_id:
            ctlpl_vm_list = util.Proxmox.filter_vm_tag(
                vm_list, config.Tag.ctlpl)
            if len(ctlpl_vm_list):
                # default to first control plane found
                existed_control_plane_vm_id = ctlpl_vm_list[0]["vmid"]
                util.log.info("existed_control_plane_vm_id",
                              existed_control_plane_vm_id, "AUTO_DETECT")

        ctlplvmctl = ControlPlaneVm(
            nodectl.api,
            nodectl.node,
            existed_control_plane_vm_id)
        join_cmd = ctlplvmctl.create_join_command()
        util.log.info("join_cmd", join_cmd)
        wkctl.exec(join_cmd)

        return new_vm_id

    def delete_worker(self,
                      vm_id,
                      vm_id_range=config.PROXMOX_VM_ID_RANGE,
                      existed_control_plane_vm_id: int = None,
                      drain_first=True,
                      **kwargs):
        nodectl = self.nodectl

        vm_list = nodectl.list_vm(vm_id_range)
        vm = util.Proxmox.filter_vm_id(vm_list, vm_id)
        vm_name = vm["name"]

        if not existed_control_plane_vm_id:
            ctlpl_vm_list = util.Proxmox.filter_vm_tag(
                vm_list, config.Tag.ctlpl)
            if len(ctlpl_vm_list):
                # default to first control plane found
                existed_control_plane_vm_id = ctlpl_vm_list[0]["vmid"]
                util.log.info("existed_control_plane_vm_id",
                              existed_control_plane_vm_id, "AUTO_DETECT")

        if existed_control_plane_vm_id:
            ctlplctl = ControlPlaneVm(
                nodectl.api, nodectl.node, existed_control_plane_vm_id)
            try:
                if drain_first:
                    ctlplctl.drain_node(vm_name)
            except Exception as err:
                util.log.error(err)
            try:
                ctlplctl.delete_node(vm_name)
            except Exception as err:
                util.log.error(err)

        vmctl = Vm(nodectl.api, nodectl.node, vm_id)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
        return vm_id
