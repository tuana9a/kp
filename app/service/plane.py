import ipaddress
from typing import List

from app.model.plane import ControlPlaneVm
from app.model.pve import PveNode
from app import util
from app.error import *
from app import config
from app.model.vm import Vm
from app.model.lb import LbVm
from app.payload import Cfg, VmResponse


class ControlPlaneService:

    def __init__(self, nodectl: PveNode) -> None:
        self.nodectl = nodectl
        pass

    def copy_kube_certs(self,
                        source_id,
                        dest_id,
                        certs=[
                            "/etc/kubernetes/pki/ca.crt",
                            "/etc/kubernetes/pki/ca.key",
                            "/etc/kubernetes/pki/sa.key",
                            "/etc/kubernetes/pki/sa.pub",
                            "/etc/kubernetes/pki/front-proxy-ca.crt",
                            "/etc/kubernetes/pki/front-proxy-ca.key",
                            "/etc/kubernetes/pki/etcd/ca.crt",
                            "/etc/kubernetes/pki/etcd/ca.key",
                        ]):
        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        nodectl = self.nodectl

        sourcectl = Vm(nodectl.api, nodectl.node, source_id)
        destctl = Vm(nodectl.api, nodectl.node, dest_id)

        for cert in certs:
            r = sourcectl.read_file(cert)
            content = r["content"]
            # TODO: check truncated content
            # https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
            r = destctl.write_file(cert, content)

    def create_control_plane(self, cfg: Cfg):
        nodectl = self.nodectl

        r = nodectl.describe_network(cfg.vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]

        new_vm_id = nodectl.new_vm_id()
        new_vm_ip = nodectl.new_vm_ip()
        new_vm_name = f"{cfg.vm_name_prefix}{new_vm_id}"

        util.log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        nodectl.clone(cfg.vm_template_id, new_vm_id)

        ctlplvmctl = ControlPlaneVm(nodectl.api, nodectl.node, new_vm_id)
        ctlplvmctl.update_config(
            name=new_vm_name,
            cpu="cputype=host",
            cores=cfg.vm_core_count,
            memory=cfg.vm_memory,
            agent="enabled=1,fstrim_cloned_disks=1",
            ciuser=cfg.vm_username,
            cipassword=cfg.vm_password,
            net0=f"virtio,bridge={cfg.vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
            sshkeys=util.Proxmox.encode_sshkeys(cfg.vm_ssh_keys),
            onboot=cfg.vm_start_on_boot,
            tags=";".join([config.Tag.ctlpl, config.Tag.kp]),
        )
        ctlplvmctl.resize_disk("scsi0", cfg.vm_disk_size)

        ctlplvmctl.startup()
        ctlplvmctl.wait_for_guest_agent()
        ctlplvmctl.wait_for_cloud_init()

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(cfg.userdata_control_plane_filepath, "r") as f:
            ctlplvmctl.write_file(userdata_location, f.read())
        ctlplvmctl.exec(f"chmod +x {userdata_location}")
        ctlplvmctl.exec(userdata_location)

        with open(cfg.containerd_config_filepath) as f:
            ctlplvmctl.write_file("/etc/containerd/config.toml", f.read())
            ctlplvmctl.restart_containerd()
            ctlplvmctl.restart_kubelet()

        existed_lb_vm_id = None
        lb_vm_list: List[VmResponse] = nodectl.detect_load_balancers()
        if len(lb_vm_list):
            existed_lb_vm_id = lb_vm_list[0].vmid
            util.log.info("existed_lb_vm_id", existed_lb_vm_id, "AUTO_DETECT")

        is_multiple_control_planes = bool(existed_lb_vm_id)
        util.log.info("is_multiple_control_planes", is_multiple_control_planes)

        # SECTION: standalone control plane
        if not is_multiple_control_planes:
            ctlplvmctl.kubeadm_init(control_plane_endpoint=new_vm_ip,
                                    pod_cidr=cfg.pod_cidr,
                                    svc_cidr=cfg.svc_cidr)
            return new_vm_id

        # SECTION: stacked control plane
        ctlpl_vm_list: List[VmResponse] = nodectl.detect_control_planes()
        existed_ctlpl_vm_id = None
        for ctlpl_vm in ctlpl_vm_list:
            ctlpl_vm_id = ctlpl_vm.vmid
            # NOTE: avoid exist id is the same with newly created one
            if ctlpl_vm_id != new_vm_id:
                existed_ctlpl_vm_id = ctlpl_vm_id
                util.log.info("existed_ctlpl_vm_id", existed_ctlpl_vm_id,
                              "AUTO_DETECT")

        # EXPLAIN: join previous control plane
        if existed_ctlpl_vm_id:
            ctlplvmctl.ensure_cert_dirs()
            self.copy_kube_certs(existed_ctlpl_vm_id, new_vm_id)
            existed_ctlplvmctl = ControlPlaneVm(
                nodectl.api, nodectl.node, existed_ctlpl_vm_id)
            join_cmd = existed_ctlplvmctl.create_join_command(
                is_control_plane=True)
            util.log.info("join_cmd", " ".join(join_cmd))
            ctlplvmctl.exec(join_cmd, timeout=20 * 60)
            return new_vm_id

        # EXPLAIN: init a fresh new control plane
        lbctl = LbVm(nodectl.api, nodectl.node, existed_lb_vm_id)
        lb_ifconfig0 = lbctl.current_config().ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect control_plane_endpoint")
        vm_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        control_plane_endpoint = vm_ip
        ctlplvmctl.kubeadm_init(control_plane_endpoint=control_plane_endpoint,
                                pod_cidr=cfg.pod_cidr,
                                svc_cidr=cfg.svc_cidr)
        return new_vm_id

    def delete_control_plane(self, cfg: Cfg, vm_id):
        nodectl = self.nodectl

        vm_list = nodectl.list_vm()
        vm: VmResponse = util.Proxmox.filter_vm_id(vm_list, vm_id)
        vm_name = vm.name
        ctlplvmctl = ControlPlaneVm(nodectl.api, nodectl.node, vm_id)
        # kubeadm reset is needed when deploying stacked control plane
        # https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-reset/#reset-workflow
        # Remove the control plane with etcd will avoid this error
        # https://serverfault.com/questions/1029654/deleting-a-control-node-from-the-cluster-kills-the-apiserver
        try:
            ctlplvmctl.kubeadm_reset()
        except Exception as err:
            util.log.error(err)

        lb_vm_list = nodectl.detect_load_balancers()
        if len(lb_vm_list):
            existed_lb_vm_id = lb_vm_list[0].vmid

        if not existed_lb_vm_id:
            ctlplvmctl.shutdown()
            ctlplvmctl.wait_for_shutdown()
            ctlplvmctl.delete()
            return

        existed_ctlpl_vm_id = None
        for x in nodectl.detect_control_planes():
            ctlpl_vm_id = x.vmid
            if ctlpl_vm_id != vm_id:
                existed_ctlpl_vm_id = ctlpl_vm_id
                break

        if existed_ctlpl_vm_id:
            ControlPlaneVm(
                nodectl.api,
                nodectl.node,
                existed_ctlpl_vm_id,
            ).delete_node(vm_name)

        ctlplvmctl.shutdown()
        ctlplvmctl.wait_for_shutdown()
        ctlplvmctl.delete()

        return vm_id
