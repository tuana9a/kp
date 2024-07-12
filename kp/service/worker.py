import ipaddress
from typing import List

from kp.error import *
from kp import util
from kp import config
from proxmoxer import ProxmoxAPI
from kp.service.plane import ControlPlaneService
from kp.service.pve import PveService
from kp.service.kube import KubeVmService, KubeadmService
from kp.service.vm import VmService
from kp.payload import Cfg, VmResponse


class WorkerService:
    @staticmethod
    def create_worker(api: ProxmoxAPI,
                      node: str,
                      cfg: Cfg):

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
                                tags=";".join([config.Tag.wk, config.Tag.kp]),
                                )
        VmService.resize_disk(api, node, new_vm_id, "scsi0", cfg.vm_disk_size)

        VmService.startup(api, node, new_vm_id)
        VmService.wait_for_guest_agent(api, node, new_vm_id)
        util.log.info("started vm", new_vm_id)

        VmService.wait_for_cloud_init(api, node, new_vm_id)
        util.log.info("waited for cloud-init", new_vm_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(cfg.userdata_worker_filepath, "r") as f:
            VmService.write_file(
                api, node, new_vm_id, userdata_location, f.read())
        VmService.exec(api, node, new_vm_id, f"chmod +x {userdata_location}")
        VmService.exec(api, node, new_vm_id, userdata_location)

        with open(cfg.containerd_config_filepath) as f:
            VmService.write_file(
                api,
                node,
                new_vm_id,
                "/etc/containerd/config.toml",
                f.read())
            KubeVmService.restart_containerd(api, node, new_vm_id)
            KubeVmService.restart_kubelet(api, node, new_vm_id)

        existed_control_plane_vm_id = None
        ctlpl_vm_list: List[VmResponse] = PveService.detect_control_planes(
            api, node, id_range=cfg.vm_id_range)
        if len(ctlpl_vm_list):
            # default to first control plane found
            existed_control_plane_vm_id = ctlpl_vm_list[0].vmid
            util.log.info("existed_control_plane_vm_id",
                          existed_control_plane_vm_id, "AUTO_DETECT")

        join_cmd = KubeadmService.create_join_command(
            api, node, existed_control_plane_vm_id)
        util.log.info("join_cmd", join_cmd)
        VmService.exec(api, node, new_vm_id, join_cmd)

        return new_vm_id

    @staticmethod
    def delete_worker(api: ProxmoxAPI,
                      node: str,
                      vm_id: str,
                      cfg: Cfg,
                      drain_first=True,
                      **kwargs):
        vm_list = PveService.list_vm(api, node, id_range=cfg.vm_id_range)
        vm: VmResponse = util.Proxmox.filter_vm_id(vm_list, vm_id)
        vm_name = vm.name

        existed_control_plane_vm_id: int = None
        if not existed_control_plane_vm_id:
            ctlpl_vm_list: List[VmResponse] = util.Proxmox.filter_vm_tag(
                vm_list, config.Tag.ctlpl)
            if len(ctlpl_vm_list):
                # default to first control plane found
                existed_control_plane_vm_id = ctlpl_vm_list[0].vmid
                util.log.info("existed_control_plane_vm_id",
                              existed_control_plane_vm_id, "AUTO_DETECT")

        if existed_control_plane_vm_id:
            if drain_first:
                ControlPlaneService.drain_node(
                    api, node, existed_control_plane_vm_id, vm_name)
            ControlPlaneService.delete_node(
                api, node, existed_control_plane_vm_id, vm_name)

        VmService.shutdown(api, node, vm_id)
        VmService.wait_for_shutdown(api, node, vm_id)
        VmService.delete(api, node, vm_id)
        return vm_id
