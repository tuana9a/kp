import os
import urllib3

from kp import util
from kp import config
from kp.util import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class MultipleControlPlanesCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("multiple-control-planes",
                         childs=[
                             InitCmd(),
                             CreateDadControlPlaneCmd(),
                             CreateChildControlPlaneCmd(),
                             DeleteControlPlaneCmd(),
                             RestoreCmd(),
                         ],
                         aliases=["ctlpls", "planes"])


class InitCmd(Cmd):
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


class CreateChildControlPlaneCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-child")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=4)
        self.parser.add_argument("--vm-mem", type=int, default=8192)
        self.parser.add_argument("--vm-disk", type=str, default="20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)
        self.parser.add_argument("--vm-containerd-config", type=str, required=True)

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
        vm_containerd_config = self.parsed_args.vm_containerd_config

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

        VmService.update_containerd_config(api, node, vmid, vm_containerd_config)
        VmService.restart_containerd(api, node, vmid)

        ControlPlaneService.ensure_cert_dirs(api, node, child_id)
        ControlPlaneService.copy_kube_certs(api, node, dad_id, child_id)
        join_cmd = ControlPlaneService.create_join_command(api,
                                                           node,
                                                           dad_id,
                                                           is_control_plane=True)
        PveApi.exec(api, node, child_id, join_cmd)


class CreateDadControlPlaneCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-dad")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--lb-id", type=int, required=True)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=4)
        self.parser.add_argument("--vm-mem", type=int, default=8192)
        self.parser.add_argument("--vm-disk", type=str, default="20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)
        self.parser.add_argument("--vm-containerd-config", type=str, required=True)

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
        vm_containerd_config = self.parsed_args.vm_containerd_config

        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

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

        VmService.update_containerd_config(api, node, dad_id, vm_containerd_config)
        VmService.restart_containerd(api, node, dad_id)
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect control_plane_endpoint")
        lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        ControlPlaneService.init(api,
                                 node,
                                 dad_id,
                                 control_plane_endpoint=lb_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return dad_id


class DeleteControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        util.log.info("dad_id", dad_id, "child_id", child_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        child_vm = PveApi.find_vm_by_id(api, node, child_id)

        VmService.kubeadm_reset(api, node, child_id)
        ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
        ControlPlaneService.delete_node(api, node, dad_id, child_vm.name)

        PveApi.shutdown(api, node, child_id)
        PveApi.wait_for_shutdown(api, node, child_id)
        PveApi.delete_vm(api, node, child_id)


class RestoreCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("restore")

    def setup(self):
        self.parser.add_argument("--lb-id", type=int, required=True)
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--backup-dir", type=str, default="/root/backup")
        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        cfg = util.load_config()
        lb_id = self.parsed_args.lb_id
        dad_id = self.parsed_args.dad_id
        backup_dir = self.parsed_args.backup_dir
        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

        util.log.info("lb_id", lb_id, "dad_id", dad_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        dad_vm = PveApi.find_vm_by_id(api, node, dad_id)
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect control_plane_endpoint")
        lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        dad_ifconfig0 = PveApi.current_config(api, node, dad_id).ifconfig(0)
        if not dad_ifconfig0:
            raise Exception("can not detect dad ip")
        dad_ip = util.Proxmox.extract_ip(dad_ifconfig0)

        VmService.kubeadm_reset(api, node, dad_id)
        cmd = f"cp -r {backup_dir}/pki/ /etc/kubernetes/"
        PveApi.exec(api, node, dad_id, cmd, interval_check=3)

        cmd = f"""/usr/local/bin/etcdutl snapshot restore {backup_dir}/etcd/member/snap/db \
            --name {dad_vm.name} \
            --initial-cluster {dad_vm.name}=https://{dad_ip}:2380 \
            --initial-cluster-token recovery-mode \
            --initial-advertise-peer-urls https://{dad_ip}:2380 \
            --skip-hash-check=true \
            --bump-revision 1000000000 --mark-compacted \
            --data-dir /var/lib/etcd
        """.split()
        PveApi.exec(api, node, dad_id, cmd, interval_check=3)

        ControlPlaneService.init(api, node, dad_id, lb_ip,
                                 extra_opts=["--ignore-preflight-errors=DirAvailable--var-lib-etcd"],
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
