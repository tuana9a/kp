import os
import ipaddress
from typing import List

from proxmoxer import ProxmoxAPI
from kp.service.pve import PveService
from kp import util
from kp import config
from kp.service.vm import VmService
from kp.payload import Cfg, VmResponse


class LbService:
    @staticmethod
    def install_haproxy(api: ProxmoxAPI,
                        node: str,
                        vm_id: str):
        cmd = ["apt", "install", "-y", "haproxy"]
        return VmService.exec(
            api, node, vm_id, cmd)

    @staticmethod
    def read_haproxy_config(api: ProxmoxAPI,
                            node: str,
                            vm_id: str,
                            config_path=config.HAPROXY_CONFIG_LOCATION):
        return VmService.read_file(api, node, vm_id, config_path)

    @staticmethod
    def update_haproxy_config(api: ProxmoxAPI,
                              node: str,
                              vm_id: str,
                              config_content: str,
                              config_path=config.HAPROXY_CONFIG_LOCATION):
        VmService.write_file(api, node, vm_id, config_path, config_content)

    @staticmethod
    def reload_haproxy(api: ProxmoxAPI,
                       node: str,
                       vm_id: str):
        cmd = ["systemctl", "reload", "haproxy"]
        VmService.exec(
            api, node, vm_id, cmd, interval_check=3)

    @staticmethod
    def create_lb(api: ProxmoxAPI,
                  node: str, cfg: Cfg):
        r = PveService.describe_network(api, node, cfg.vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]

        new_vm_id = PveService.new_vm_id(
            api,
            node,
            id_range=cfg.vm_id_range,
            preserved_ids=cfg.vm_preserved_ids)
        new_vm_ip = PveService.new_vm_ip(
            api,
            node,
            cfg.vm_network_name,
            id_range=cfg.vm_id_range,
            preserved_ips=cfg.vm_preserved_ips)
        new_vm_name = f"{cfg.vm_name_prefix}{new_vm_id}"

        util.log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        PveService.clone(api, node, cfg.vm_template_id, new_vm_id)

        VmService.update_config(api, node, new_vm_id,
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
        VmService.resize_disk(api, node, new_vm_id, "scsi0", cfg.vm_disk_size)

        VmService.startup(api, node, new_vm_id)
        VmService.wait_for_guest_agent(api, node, new_vm_id)
        VmService.wait_for_cloud_init(api, node, new_vm_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(cfg.userdata_loadbalancer_filepath, "r") as f:
            VmService.write_file(
                api, node, new_vm_id, userdata_location, f.read())
        VmService.exec(api, node, new_vm_id, f"chmod +x {userdata_location}")
        VmService.exec(api, node, new_vm_id, userdata_location)

        ctlpl_list = PveService.detect_control_planes(
            api, node, id_range=cfg.vm_id_range)
        backends = []
        for x in ctlpl_list:
            vmid = x.vmid
            ifconfig0 = VmService.current_config(api, node, vmid).ifconfig(0)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                backends.append([vmid, vmip])
        backends_content = util.Haproxy.render_backends_config(backends)
        content = config.HAPROXY_CONFIG_TEMPLATE.format(
            control_plane_backends=backends_content)
        # if using the roll_lb method then the backends placeholder will
        # not be there, so preserve the old haproxy.cfg
        LbService.update_haproxy_config(api, node, new_vm_id, content)
        LbService.reload_haproxy(api, node, new_vm_id)

        return new_vm_id
