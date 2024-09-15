import os
import urllib3
import ipaddress

from kp import util
from kp import config
from kp.model import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class DadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("dad",
                         childs=[
                             CreateDadCmd(),
                             InitDadCmd(),
                         ],
                         aliases=[])


class CreateDadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--lb-id", type=int, required=False)
        self.parser.add_argument("--vip", type=str, required=False)
        self.parser.add_argument("--vip-inf", type=str, default="eth0")

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

        dad_id = self.parsed_args.dad_id
        lb_id = self.parsed_args.lb_id
        template_id = self.parsed_args.template_id
        vip = self.parsed_args.vip
        vip_inf = self.parsed_args.vip_inf

        if not lb_id and not vip:
            raise Exception("unknow type of control plane deployment, must be: --lb-id or --vip")

        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(dad_id)
        vm_cores = self.parsed_args.vm_cores
        vm_mem = self.parsed_args.vm_mem
        vm_disk_size = self.parsed_args.vm_disk
        vm_username = self.parsed_args.vm_username
        vm_password = self.parsed_args.vm_password
        vm_network = self.parsed_args.vm_net
        vm_ip = self.parsed_args.vm_ip
        vm_start_on_boot = self.parsed_args.vm_start_on_boot
        r = PveApi.describe_network(api, node, vm_network)
        network_gw_ip = str(ipaddress.IPv4Interface(r["cidr"]).ip) or r["address"]

        vm_userdata = self.parsed_args.vm_userdata

        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

        PveApi.clone(api, node, template_id, dad_id)
        PveApi.update_config(api, node, dad_id,
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
        PveApi.resize_disk(api, node, dad_id, "scsi0", vm_disk_size)

        PveApi.startup(api, node, dad_id)
        PveApi.wait_for_guestagent(api, node, dad_id)
        PveApi.wait_for_cloudinit(api, node, dad_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, dad_id, userdata_location, f.read())
        PveApi.exec(api, node, dad_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, dad_id, userdata_location)

        VmService.update_containerd_config(api, node, dad_id)
        VmService.restart_containerd(api, node, dad_id)
        plane_endpoint = None

        if lb_id:
            lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
            if not lb_ifconfig0:
                raise Exception("can not detect control_plane_endpoint")
            lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
            plane_endpoint = lb_ip

        if vip:
            kubevip_manifest = util.Kubevip.render_pod_manifest(inf=vip_inf, vip=vip)
            ControlPlaneService.install_static_pod(api, node, dad_id, config.KUBEVIP_MANIFEST_FILENAME, kubevip_manifest)
            plane_endpoint = vip

        ControlPlaneService.init(api,
                                 node,
                                 dad_id,
                                 control_plane_endpoint=plane_endpoint,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return dad_id


class InitDadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("init")

    def setup(self):
        self.parser.add_argument("--lb-id", type=int, required=True)
        self.parser.add_argument("--plane-id", type=int, required=True)
        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        lb_id = self.parsed_args.lb_id
        plane_id = self.parsed_args.plane_id
        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect lb ip for control_plane_endpoint")
        lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        ControlPlaneService.init(api,
                                 node,
                                 plane_id,
                                 control_plane_endpoint=lb_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
