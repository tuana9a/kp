import os
import urllib3
import ipaddress

from kp import util
from kp import config
from kp.model import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi

from kp.cmd.etcd import EtcdCmd
from kp.cmd.vip import KubevipCmd
from kp.cmd.kubeconfig import KubeconfigCmd
from kp.cmd.planes.standalone import StandaloneCmd
from kp.cmd.planes.dad import DadCmd
from kp.cmd.planes.child import ChildCmd


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             StandaloneCmd(),
                             KubeconfigCmd(),
                             DistributeCertsCmd(),
                             JoinCmd(),
                             EtcdCmd(),
                             DadCmd(),
                             ChildCmd(),
                             KubevipCmd(),
                             CreateJoinCmd(),
                         ],
                         aliases=["plane"])


class DistributeCertsCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("distribute-certs", aliases=["dist-certs", "copy-certs", "replicate-certs"])

    def setup(self):
        self.parser.add_argument("src_id", type=int)
        self.parser.add_argument("dest_id", type=int)

    def run(self):
        src_id = self.parsed_args.src_id
        dest_id = self.parsed_args.dest_id
        urllib3.disable_warnings()
        util.log.info("src", src_id, "dest", dest_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ControlPlaneService.ensure_cert_dirs(api, node, dest_id)
        ControlPlaneService.copy_kube_certs(api, node, src_id, dest_id)


class JoinCmd(Cmd):

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
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        util.log.info("dad", dad_id, "child", child_id)

        ControlPlaneService.ensure_cert_dirs(api, node, child_id)
        ControlPlaneService.copy_kube_certs(api, node, dad_id, child_id)
        join_cmd = ControlPlaneService.create_join_command(api,
                                                           node,
                                                           dad_id,
                                                           is_control_plane=True)
        PveApi.exec(api, node, child_id, join_cmd)


class CreateJoinCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-join-command")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        util.log.info("vmid", vmid, "create-join-token")
        ControlPlaneService.create_join_command(api, node, vmid)
