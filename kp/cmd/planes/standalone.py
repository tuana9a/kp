import os
import urllib3
import ipaddress

from kp import util
from kp import config
from kp.model import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class StandaloneCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("standalone",
                         childs=[
                             CreateStandaloneCmd(),
                             DeleteStandaloneCmd(),
                         ],
                         aliases=["alone"])


class CreateStandaloneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=2)
        self.parser.add_argument("--vm-mem", type=int, default=4096)
        self.parser.add_argument("--vm-disk", type=str, default="+20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)

        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        vmid = self.parsed_args.vmid
        template_id = self.parsed_args.template_id
        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(vmid)
        vm_cores = self.parsed_args.vm_cores
        vm_mem = self.parsed_args.vm_mem
        vm_disk_size = self.parsed_args.vm_disk
        vm_username = self.parsed_args.vm_username
        vm_password = self.parsed_args.vm_password
        vm_network = self.parsed_args.vm_net
        vm_ip = self.parsed_args.vm_ip
        vm_start_on_boot = self.parsed_args.vm_start_on_boot
        r = PveApi.describe_network(api, node, vm_network)
        network_gw_ip = str(ipaddress.IPv4Interface(r["cidr"]).ip) \
            or r["address"]

        vm_userdata = self.parsed_args.vm_userdata

        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

        PveApi.update_config(api, node, vmid,
                             name=new_vm_name,
                             cpu="cputype=host",
                             cores=vm_cores,
                             memory=vm_mem,
                             agent="enabled=1,fstrim_cloned_disks=1",
                             ciuser=vm_username,
                             cipassword=vm_password,
                             net0=f"virtio,bridge={vm_network}",
                             ipconfig0=f"ip={vm_ip}/24,gw={network_gw_ip}",
                             sshkeys=util.Proxmox.encode_sshkeys(cfg.vm_ssh_keys),
                             onboot=vm_start_on_boot,
                             tags=";".join([config.Tag.kp]),
                             )
        PveApi.resize_disk(api, node, vmid, "scsi0", vm_disk_size)

        PveApi.startup(api, node, vmid)
        PveApi.wait_for_guestagent(api, node, vmid)
        PveApi.wait_for_cloudinit(api, node, vmid)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, vmid, userdata_location, f.read())
        PveApi.exec(api, node, vmid, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, vmid, userdata_location)

        VmService.update_containerd_config(api, node, vmid)
        VmService.restart_containerd(api, node, vmid)

        ControlPlaneService.init(api,
                                 node,
                                 vmid,
                                 control_plane_endpoint=vm_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return vmid


class DeleteStandaloneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        vm_id = self.parsed_args.vmid
        util.log.info("vm_id", vm_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        VmService.kubeadm_reset(api, node, vm_id)
        PveApi.shutdown(api, node, vm_id)
        PveApi.wait_for_shutdown(api, node, vm_id)
        PveApi.delete_vm(api, node, vm_id)
