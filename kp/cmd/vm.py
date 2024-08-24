import os
import urllib3
import ipaddress

from kp import util
from kp.util import Cmd
from kp.service.vm import VmService
from kp.client.pve import PveApi
from kp import config


class VmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__(
            "vm",
            childs=[
                RebootVmCmd(),
                RemoveVmCmd(),
                StartVmCmd(),
                CopyFileCmd(),
                CloneVmCmd(),
                UpdateConfigCmd(),
                WaitForGuestAgentCmd(),
                WaitForCloudInitCmd(),
                RunUserDataCmd(),
                UpdateContainerdConfigCmd(),
                RestartKubeletCmd(),
                KubeadmResetCmd(),
            ])


class RebootVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("reboot")

    def setup(self):
        self.parser.add_argument("ids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        ids = self.parsed_args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        for vmid in ids:
            PveApi.reboot(api, node, vmid)


class RemoveVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def setup(self):
        self.parser.add_argument("ids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        ids = self.parsed_args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        for vmid in ids:
            PveApi.shutdown(api, node, vmid)
            PveApi.wait_for_shutdown(api, node, vmid)
            PveApi.delete_vm(api, node, vmid)


class StartVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("start", aliases=["run", "up"])

    def setup(self):
        self.parser.add_argument("ids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        ids = self.parsed_args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        for vmid in ids:
            PveApi.startup(api, node, vmid)


class WaitForGuestAgentCmd(Cmd):
    def __init__(self):
        super().__init__("wait-guestagent")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        vmid = self.parsed_args.vmid
        util.log.info("vmid", vmid)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        PveApi.wait_for_guestagent(api, node, vmid)


class WaitForCloudInitCmd(Cmd):
    def __init__(self):
        super().__init__("wait-cloudinit")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        vmid = self.parsed_args.vmid
        util.log.info("vmid", vmid)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        PveApi.wait_for_cloudinit(api, node, vmid)


class CopyFileCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-file", aliases=["cp"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("localpath", type=str)
        self.parser.add_argument("path", type=str)

    def run(self):
        localpath = self.parsed_args.localpath
        path = self.parsed_args.path
        vm_id = self.parsed_args.vmid
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        util.log.info(localpath, "->", path)
        with open(localpath, "r", encoding="utf-8") as f:
            PveApi.write_file(api, node, vm_id, path, f.read())


class CloneVmCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("clone", aliases=["cl"])

    def setup(self):
        self.parser.add_argument("srcid", type=int)
        self.parser.add_argument("destid", type=int)

    def run(self):
        src_id = self.parsed_args.srcid
        dest_id = self.parsed_args.destid
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        PveApi.clone(api, node, src_id, dest_id)


class UpdateConfigCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("update-config")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=2)
        self.parser.add_argument("--vm-mem", type=int, default=2048)
        self.parser.add_argument("--vm-disk", type=str, default="+20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
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
                             tags=";".join([config.Tag.kp]))

        PveApi.resize_disk(api, node, vmid, "scsi0", vm_disk_size)


class RunUserDataCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("run-userdata")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("userdata", type=str)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        userdata = self.parsed_args.userdata
        vm_userdata = "/usr/local/bin/userdata.sh"
        with open(userdata, "r") as f:
            PveApi.write_file(api, node, vmid, vm_userdata, f.read())
        PveApi.exec(api, node, vmid, f"chmod +x {vm_userdata}")
        PveApi.exec(api, node, vmid, vm_userdata)


class UpdateContainerdConfigCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("update-containerd-config")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("filepath", type=str)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        filepath = self.parsed_args.filepath
        with open(filepath, "r") as f:
            VmService.update_containerd_config(api, node, vmid, f.read())
            VmService.restart_containerd(api, node, vmid)


class RestartKubeletCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("restart-kubelet")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        VmService.restart_kubelet(api, node, vmid)


class KubeadmResetCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("kubeadm-reset")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        VmService.kubeadm_reset(api, node, vmid)
