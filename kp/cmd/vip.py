import os
import urllib3
import ipaddress

from kp import config
from kp import util
from kp.model import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class KubevipCmd(Cmd):
    def __init__(self):
        super().__init__("kube-vip", childs=[
            InstallKubevipCmd(),
            UninstallKubevipCmd(),
        ],
            aliases=["vip"])


class InstallKubevipCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("install")

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


class UninstallKubevipCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("uninstall")

    def setup(self):
        self.parser.add_argument("plane_ids", nargs="+")

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        plane_ids = self.parsed_args.plane_ids
        for vmid in plane_ids:
            ControlPlaneService.uninstall_static_pod(api, node, vmid, config.KUBEVIP_MANIFEST_FILENAME)
