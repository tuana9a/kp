import os
import urllib3

from kp import util
from kp.util import Cmd
from kp.service.vm import VmService


class VmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__(
            "vm",
            childs=[RebootVmCmd(),
                    RemoveVmCmd(),
                    StartVmCmd(),
                    CopyFileCmd()])


class RebootVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("reboot")

    def setup(self):
        self.parser.add_argument("ids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        args = self.parsed_args

        ids = args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        for vmid in ids:
            VmService.reboot(api, node, vmid)


class RemoveVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def setup(self):
        self.parser.add_argument("ids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        ids = args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        for vmid in ids:
            VmService.shutdown(api, node, vmid)
            VmService.wait_for_shutdown(api, node, vmid)
            VmService.delete(api, node, vmid)


class StartVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("start", aliases=["run", "up"])

    def setup(self):
        self.parser.add_argument("ids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        args = self.parsed_args

        ids = args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        for vmid in ids:
            VmService.startup(api, node, vmid)
            VmService.wait_for_guest_agent(api, node, vmid)


class CopyFileCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-file", aliases=["cp"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("localpath", type=str)
        self.parser.add_argument("path", type=str)

    def run(self):
        args = self.parsed_args
        localpath = args.localpath
        path = args.path
        vm_id = args.vmid
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        util.log.info(localpath, "->", path)
        with open(localpath, "r", encoding="utf-8") as f:
            VmService.write_file(api, node, vm_id, path, f.read())
