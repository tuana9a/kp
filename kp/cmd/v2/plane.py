import os
import urllib3
import ipaddress

from kp import config
from kp import util
from kp.util import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class V2Cmd(Cmd):
    def __init__(self):
        super().__init__("v2", childs=[
            InstallKubevipCmd(),
            CreateChildCmd(),
        ])


class InstallKubevipCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("install-kube-vip")

    def setup(self):
        self.parser.add_argument("plane_ids", nargs="+")
        self.parser.add_argument("--vip", type=str, required=True)
        self.parser.add_argument("--inf", "--interface", type=str, required=True)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        plane_ids = self.parsed_args.plane_ids
        vip = self.parsed_args.vip
        inf = self.parsed_args.inf
        manifest = util.Kubevip.render_pod_manifest(inf=inf, vip=vip)
        for vmid in plane_ids:
            ControlPlaneService.install_static_pod(api, node, vmid, config.KUBEVIP_MANIFEST_FILENAME, manifest)


class CreateDadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-dad")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--vip", type=str, required=True)
        self.parser.add_argument("--inf", type=str, default="eth0")

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
        vip = self.parsed_args.vip
        inf = self.parsed_args.inf
        template_id = self.parsed_args.template_id
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
        network_gw_ip = str(ipaddress.IPv4Interface(r["cidr"]).ip) \
            or r["address"]

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
        kubevip_manifest = util.Kubevip.render_pod_manifest(inf=inf, vip=vip)
        ControlPlaneService.install_static_pod(api, node, dad_id, config.KUBEVIP_MANIFEST_FILENAME, kubevip_manifest)
        ControlPlaneService.init(api,
                                 node,
                                 dad_id,
                                 control_plane_endpoint=vip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return dad_id


class CreateChildCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-child")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

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

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        template_id = self.parsed_args.template_id
        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(child_id)
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

        PveApi.clone(api, node, template_id, child_id)
        PveApi.update_config(api, node, child_id,
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
        PveApi.resize_disk(api, node, child_id, "scsi0", vm_disk_size)

        PveApi.startup(api, node, child_id)
        PveApi.wait_for_guestagent(api, node, child_id)
        PveApi.wait_for_cloudinit(api, node, child_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, child_id, userdata_location, f.read())
        PveApi.exec(api, node, child_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, child_id, userdata_location)

        VmService.update_containerd_config(api, node, child_id)
        VmService.restart_containerd(api, node, child_id)

        ControlPlaneService.ensure_cert_dirs(api, node, child_id)
        ControlPlaneService.copy_kube_certs(api, node, dad_id, child_id)
        join_cmd = ControlPlaneService.create_join_command(api,
                                                           node,
                                                           dad_id,
                                                           is_control_plane=True)
        PveApi.exec(api, node, child_id, join_cmd)
        # kube-vip.yaml
        kubevip_manifest_path = os.path.join(config.KUBERNETES_STATIC_POD_DIR, config.KUBEVIP_MANIFEST_FILENAME)
        PveApi.copy_file_vm2vm(api, node, dad_id, child_id, kubevip_manifest_path)
