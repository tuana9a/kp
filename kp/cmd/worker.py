import os
import urllib3
import ipaddress

from kp import util
from kp.util import Cmd
from kp import config
from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService


class WorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("worker",
                         childs=[
                             CreateWorkerCmd(),
                             DeleteWorkerCmd(),
                             JoinWorkerCmd(),
                             UpgradeCmd(),
                         ],
                         aliases=["wk"])


class CreateWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create", aliases=["add"])

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=4)
        self.parser.add_argument("--vm-mem", type=int, default=8192)
        self.parser.add_argument("--vm-disk", type=str, default="32G")
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
                             tags=";".join([config.Tag.kp]))

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

        join_cmd = ControlPlaneService.create_join_command(api, node, dad_id)
        PveApi.exec(api, node, child_id, join_cmd)


class DeleteWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        util.log.info("dad_id", dad_id, "child_id", child_id)

        child_vm = PveApi.find_vm_by_id(api, node, child_id)
        ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
        ControlPlaneService.delete_node(api, node, dad_id, child_vm.name)

        PveApi.shutdown(api, node, child_id)
        PveApi.wait_for_shutdown(api, node, child_id)
        PveApi.delete_vm(api, node, child_id)


class JoinWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        plane_id = self.parsed_args.dad_id
        worker_id = self.parsed_args.child_id
        util.log.info("plane", plane_id, "worker", worker_id)
        join_cmd = ControlPlaneService.create_join_command(api, node, plane_id)
        PveApi.exec(api, node, worker_id, join_cmd)


class UpgradeCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("upgrade")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)
        self.parser.add_argument("--kubernetes-semver", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        kubernetes_version_minor = ".".join(self.parsed_args.kubernetes_semver.split(".")[0:2])
        kubernetes_version_patch = ".".join(self.parsed_args.kubernetes_semver.split(".")[0:3])

        child_vm = PveApi.find_vm_by_id(api, node, child_id)

        vm_userdata = "/usr/local/bin/upgrade.sh"
        tmpl = config.UPGRADE_WORKER_SCRIPT
        userdata_content = tmpl.format(kubernetes_version_minor=kubernetes_version_minor,
                                       kubernetes_version_patch=kubernetes_version_patch)
        PveApi.write_file(api, node, child_id, vm_userdata, userdata_content)
        PveApi.exec(api, node, child_id, f"chmod +x {vm_userdata}")
        PveApi.exec(api, node, child_id, vm_userdata)
        PveApi.exec(api, node, child_id, "sudo kubeadm upgrade node".split())

        ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
        """
        # NOTE: with quote at package version will not work
        # Eg: apt install -y kubelet="1.29.6-*"
            2024-07-16 00:18:22 [DEBUG] pve-cobi 128 exec 333843 stderr
            E: Version '"1.29.6-*"' for 'kubelet' was not found
            E: Version '"1.29.6-*"' for 'kubectl' was not found
        # I think is because of shell text processing
        """
        cmd = f"apt install -y kubelet={kubernetes_version_patch}-* kubectl={kubernetes_version_patch}-*".split()
        PveApi.exec(api, node, child_id, cmd)
        VmService.systemctl_daemon_reload(api, node, child_id)
        VmService.restart_kubelet(api, node, child_id)
        ControlPlaneService.uncordon_node(api, node, dad_id, child_vm.name)
