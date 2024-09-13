import os
import urllib3
import ipaddress

from kp import util
from kp import config
from kp.model import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class KubeconfigCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("kubeconfig",
                         childs=[
                             ViewKubeConfigCmd(),
                             SaveKubeConfigCmd(),
                         ],
                         aliases=[])


class ViewKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("view", aliases=["cat"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")

    def run(self):
        vm_id = self.parsed_args.vmid
        filepath = self.parsed_args.file_path
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        _, stdout, _ = ControlPlaneService.cat_kubeconfig(
            api, node, vm_id, filepath)
        print(stdout)


class SaveKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("save")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")
        self.parser.add_argument("-o",
                                 "--output",
                                 default="~/.kube/config")

    def run(self):
        vm_id = self.parsed_args.vmid
        filepath = self.parsed_args.file_path
        output = self.parsed_args.output
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        _, stdout, _ = ControlPlaneService.cat_kubeconfig(
            api, node, vm_id, filepath)
        with open(output, "w") as f:
            f.write(stdout)
