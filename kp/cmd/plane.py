import os
import urllib3

from kp import util
from kp import config
from kp.util import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.service.pve import PveService
from kp.service.kube import KubeadmService


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             CreateControlPlaneCmd(),
                             DeleteControlPlaneCmd(),
                             KubeConfigCmd(),
                             CopyKubeCertsCmd(),
                             JoinControlPlaneCmd(),
                         ],
                         aliases=["ctlpl", "plane"])


class CreateControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create", aliases=["add"])

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ControlPlaneService.create_control_plane(api, node, cfg)


class DeleteControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        util.log.info("vm_id", vm_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ControlPlaneService.delete_control_plane(api, node, vm_id, cfg)


class KubeConfigCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("kubeconfig", childs=[
            ViewKubeConfigCmd(),
            SaveKubeConfigCmd(),
        ])


class ViewKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("view", aliases=["cat"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")

    def run(self):
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
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
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
        output = args.output
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        _, stdout, _ = ControlPlaneService.cat_kubeconfig(
            api, node, vm_id, filepath)
        with open(output, "w") as f:
            f.write(stdout)


class CopyKubeCertsCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-certs")

    def setup(self):
        self.parser.add_argument("source", type=int)
        self.parser.add_argument("dest", type=int)

    def run(self):
        args = self.parsed_args
        source_id = args.source
        dest_id = args.dest
        urllib3.disable_warnings()
        util.log.info("src", source_id, "dest", dest_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ControlPlaneService.ensure_cert_dirs(api, node, dest_id)
        ControlPlaneService.copy_kube_certs(api, node, source_id, dest_id)


class JoinControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def setup(self):
        self.parser.add_argument("ctlplids", nargs="+", type=int)

    def run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        control_plane_ids = args.ctlplids
        child_ids_set = set(control_plane_ids)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ctlpl_list = PveService.detect_control_planes(
            api, node, id_range=cfg.vm_id_range)

        if not len(ctlpl_list):
            util.log.info("can't find any control planes")
            return

        for x in ctlpl_list:
            vm_id = x.vmid
            if vm_id not in child_ids_set:
                control_plane_id = vm_id
                break

        if not control_plane_id:
            util.log.info("can't find dad control plane")
            return

        util.log.info("dad", control_plane_id, "childs", control_plane_ids)

        join_cmd = KubeadmService.create_join_command(
            api, node, control_plane_id, is_control_plane=True)

        # EXPLAIN: need to join and update the tags before detect control plane
        # by tag
        for vmid in control_plane_ids:
            ControlPlaneService.ensure_cert_dirs(api, node, vm_id)
            ControlPlaneService.copy_kube_certs(
                api, node, control_plane_id, vmid)
            VmService.exec(api, node, vmid, join_cmd)
            VmService.update_config(
                api, node, vmid, tags=[
                    config.Tag.ctlpl, config.Tag.kp])
