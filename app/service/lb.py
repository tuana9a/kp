import os
import ipaddress

from app.model.pve import PveNode
from app import util
from app import config
from app.model.lb import LbVm


class LbService:

    def __init__(self, nodectl: PveNode) -> None:
        self.nodectl = nodectl
        pass

    def create_lb(self,
                  vm_network_name,
                  vm_template_id: int,
                  haproxy_cfg: str,
                  install_kubectl_filepath: str = None,
                  preserved_ips=[],
                  vm_id_range=config.PROXMOX_VM_ID_RANGE,
                  vm_core_count=2,
                  vm_memory=4096,
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
        for vmip in vm_network.hosts():
            ip_pool.append(str(vmip))
        preserved_ips.append(network_gw_ip)
        util.log.debug("preserved_ips", preserved_ips)

        vm_list = nodectl.list_vm(vm_id_range)
        new_vm_id = nodectl.new_vm_id(vm_list, vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(vm_list, ip_pool, preserved_ips)
        new_vm_name = f"{vm_name_prefix}{new_vm_id}"

        util.log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        nodectl.clone(vm_template_id, new_vm_id)

        lbctl = LbVm(nodectl.api, nodectl.node, new_vm_id)
        lbctl.update_config(
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
            tags=";".join([config.Tag.lb, config.Tag.kp]),
        )
        lbctl.resize_disk("scsi0", vm_disk_size)

        lbctl.startup()
        lbctl.wait_for_guest_agent()
        lbctl.wait_for_cloud_init()

        lbctl.install_haproxy()

        if not os.path.exists(haproxy_cfg):
            raise FileNotFoundError(haproxy_cfg)

        with open(haproxy_cfg, "r", encoding="utf8") as f:
            content = f.read()
            ctlpl_list = nodectl.detect_control_planes(vm_id_range=vm_id_range)
            backends_content = util.Haproxy.render_backends_config(ctlpl_list)
            content = content.format(control_plane_backends=backends_content)
            # if using the roll_lb method then the backends placeholder will
            # not be there, so preserve the old haproxy.cfg
            lbctl.update_haproxy_config(content)
            lbctl.reload_haproxy()

        if install_kubectl_filepath:
            vm_install_kubectl_location = "/usr/local/bin/install-kubectl.sh"
            with open(install_kubectl_filepath, "r") as f:
                lbctl.write_file(vm_install_kubectl_location, f.read())
            lbctl.exec(f"chmod +x {vm_install_kubectl_location}")
            lbctl.exec(vm_install_kubectl_location)

        return new_vm_id
