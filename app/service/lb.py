import os
import ipaddress
from typing import List

from app.model.pve import PveNode
from app import util
from app import config
from app.model.lb import LbVm
from app.model.vm import Vm
from app.payload import Cfg, VmResponse


class LbService:

    def __init__(self, nodectl: PveNode) -> None:
        self.nodectl = nodectl
        pass

    def create_lb(self, cfg: Cfg):
        nodectl = self.nodectl
        r = nodectl.describe_network(cfg.vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for vmip in vm_network.hosts():
            ip_pool.append(str(vmip))
        cfg.vm_preserved_ips.append(network_gw_ip)
        util.log.debug("preserved_ips", cfg.vm_preserved_ips)

        vm_list: List[VmResponse] = nodectl.list_vm(cfg.vm_id_range)
        new_vm_id = nodectl.new_vm_id(vm_list, cfg.vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(vm_list, ip_pool, cfg.vm_preserved_ips)
        new_vm_name = f"{cfg.vm_name_prefix}{new_vm_id}"

        util.log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        nodectl.clone(cfg.vm_template_id, new_vm_id)

        lbctl = LbVm(nodectl.api, nodectl.node, new_vm_id)
        lbctl.update_config(
            name=new_vm_name,
            cpu="cputype=host",
            cores=cfg.vm_core_count,
            memory=cfg.vm_memory,
            ciuser=cfg.vm_username,
            cipassword=cfg.vm_password,
            sshkeys=util.Proxmox.encode_sshkeys(cfg.vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={cfg.vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
            onboot=cfg.vm_start_on_boot,
            tags=";".join([config.Tag.lb, config.Tag.kp]),
        )
        lbctl.resize_disk("scsi0", cfg.vm_disk_size)

        lbctl.startup()
        lbctl.wait_for_guest_agent()
        lbctl.wait_for_cloud_init()

        lbctl.install_haproxy()

        if not os.path.exists(cfg.haproxy_cfg):
            raise FileNotFoundError(cfg.haproxy_cfg)

        with open(cfg.haproxy_cfg, "r", encoding="utf8") as f:
            content = f.read()
            ctlpl_list = nodectl.detect_control_planes(
                vm_id_range=cfg.vm_id_range)
            backends = []
            for x in ctlpl_list:
                vmid = x.vmid
                ifconfig0 = Vm(nodectl.api, nodectl.node,
                               vmid).current_config().ifconfig(0)
                if ifconfig0:
                    vmip = util.Proxmox.extract_ip(ifconfig0)
                    backends.append([vmid, vmip])
            backends_content = util.Haproxy.render_backends_config(backends)
            content = content.format(control_plane_backends=backends_content)
            # if using the roll_lb method then the backends placeholder will
            # not be there, so preserve the old haproxy.cfg
            lbctl.update_haproxy_config(content)
            lbctl.reload_haproxy()

        if cfg.install_kubectl_filepath:
            vm_install_kubectl_location = "/usr/local/bin/install-kubectl.sh"
            with open(cfg.install_kubectl_filepath, "r") as f:
                lbctl.write_file(vm_install_kubectl_location, f.read())
            lbctl.exec(f"chmod +x {vm_install_kubectl_location}")
            lbctl.exec(vm_install_kubectl_location)

        return new_vm_id
