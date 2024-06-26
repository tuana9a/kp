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

        new_vm_id = nodectl.new_vm_id()
        new_vm_ip = nodectl.new_vm_ip()
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

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(cfg.userdata_loadbalancer_filepath, "r") as f:
            lbctl.write_file(userdata_location, f.read())
        lbctl.exec(f"chmod +x {userdata_location}")
        lbctl.exec(userdata_location)

        ctlpl_list = nodectl.detect_control_planes()
        backends = []
        for x in ctlpl_list:
            vmid = x.vmid
            ifconfig0 = Vm(nodectl.api, nodectl.node,
                           vmid).current_config().ifconfig(0)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                backends.append([vmid, vmip])
        backends_content = util.Haproxy.render_backends_config(backends)
        content = config.HAPROXY_CONFIG_TEMPLATE.format(
            control_plane_backends=backends_content)
        # if using the roll_lb method then the backends placeholder will
        # not be there, so preserve the old haproxy.cfg
        lbctl.update_haproxy_config(content)
        lbctl.reload_haproxy()

        return new_vm_id
