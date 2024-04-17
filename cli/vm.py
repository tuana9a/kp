import os
import urllib3

from app import util
from cli.core import Cmd
from app.model.pve import PveNode
from app.model.vm import Vm


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

    def _setup(self):
        self.parser.add_argument("ids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args

        ids = args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = util.Proxmox.create_api_client(**cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        for id in ids:
            vmctl = Vm(nodectl.api, nodectl.node, id)
            vmctl.reboot()


class RemoveVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def _setup(self):
        self.parser.add_argument("ids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args

        ids = args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = util.Proxmox.create_api_client(**cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        for id in ids:
            vmctl = Vm(nodectl.api, nodectl.node, id)
            vmctl.shutdown()
            vmctl.wait_for_shutdown()
            vmctl.delete()


class StartVmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("start", aliases=["run", "up"])

    def _setup(self):
        self.parser.add_argument("ids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args

        ids = args.ids
        util.log.info("vm_ids", ids)
        cfg = util.load_config()
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = util.Proxmox.create_api_client(**cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        for id in ids:
            vmctl = Vm(nodectl.api, nodectl.node, id)
            vmctl.startup()
            vmctl.wait_for_guest_agent()


class CopyFileCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-file", aliases=["cp"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("localpath", type=str)
        self.parser.add_argument("path", type=str)

    def _run(self):
        args = self.parsed_args
        localpath = args.localpath
        path = args.path
        vm_id = args.vmid
        urllib3.disable_warnings()

        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = util.Proxmox.create_api_client(**cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        vmctl = Vm(nodectl.api, nodectl.node, vm_id)
        util.log.info(localpath, "->", path)
        with open(localpath, "r", encoding="utf-8") as f:
            vmctl.write_file(path, f.read())
