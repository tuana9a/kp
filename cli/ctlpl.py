import os
import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.service.ctlpl import ControlPlaneService
from app import util
from app import config


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             CreateControlPlaneCmd(),
                             DeleteControlPlaneCmd(),
                             CatKubeConfigCmd(),
                             CopyKubeCertsCmd(),
                             JoinControlPlaneCmd(),
                         ],
                         aliases=["ctlpl"])


class CreateControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create", aliases=["add"])

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()

        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)

        service = ControlPlaneService(nodectl, log=log)
        service.create_control_plane(**cfg)


class DeleteControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        log.info("vm_id", vm_id)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        clusterctl = ControlPlaneService(nodectl, log=log)
        clusterctl.delete_control_plane(vm_id, **cfg)


class CatKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("cat-kubeconfig", aliases=["kubeconfig"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")

    def _run(self):
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
        urllib3.disable_warnings()
        log = Logger.from_env()
        log.info("vm_id", vm_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        ctlplvmctl = nodectl.ctlplvmctl(vm_id)
        _, stdout, _ = ctlplvmctl.cat_kubeconfig(filepath)
        print(stdout)


class CopyKubeCertsCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-certs")

    def _setup(self):
        self.parser.add_argument("source", type=int)
        self.parser.add_argument("dest", type=int)

    def _run(self):
        args = self.parsed_args
        source_id = args.source
        dest_id = args.dest
        urllib3.disable_warnings()
        log = Logger.from_env()
        log.info("src", source_id, "dest", dest_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        nodectl.ctlplvmctl(dest_id).ensure_cert_dirs()
        service = ControlPlaneService(nodectl, log=log)
        service.copy_kube_certs(source_id, dest_id)


class JoinControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def _setup(self):
        self.parser.add_argument("ctlplids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        args = self.parsed_args
        control_plane_ids = args.ctlplids
        child_ids_set = set(control_plane_ids)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        service = ControlPlaneService(nodectl, log=log)
        ctlpl_list = nodectl.detect_control_planes(
            vm_id_range=cfg["vm_id_range"])

        if not len(ctlpl_list):
            log.info("can't find any control planes")
            return

        for ctlpl_vm in ctlpl_list:
            ctlpl_vm_id = ctlpl_vm["vmid"]
            if ctlpl_vm_id not in child_ids_set:
                control_plane_id = ctlpl_vm_id
                break

        if not control_plane_id:
            log.info("can't find dad control plane")
            return

        log.info("dad", control_plane_id, "childs", control_plane_ids)

        lb_vm_list = nodectl.detect_load_balancers(cfg["vm_id_range"])

        if not len(lb_vm_list):
            log.info("can't not find load balancers")
            return

        lb_vm_id = lb_vm_list[0]["vmid"]
        lbctl = nodectl.lbctl(lb_vm_id)
        dadctl = nodectl.ctlplvmctl(control_plane_id)
        join_cmd = dadctl.kubeadm.create_join_command(is_control_plane=True)

        # EXPLAIN: need to join and update the tags before detect control plane by tag
        for id in control_plane_ids:
            ctlplvmctl = nodectl.ctlplvmctl(id)
            ctlplvmctl.ensure_cert_dirs()
            service.copy_kube_certs(control_plane_id, id)
            ctlplvmctl.exec(join_cmd)
            ctlplvmctl.update_config(tags=[config.Tag.ctlpl, config.Tag.kp])

        with open(cfg["haproxy_cfg"], "r", encoding="utf8") as f:
            content = f.read()
            ctlpl_list = nodectl.detect_control_planes(
                vm_id_range=cfg["vm_id_range"])
            backends_content = util.Haproxy.render_backends_config(ctlpl_list)
            content = content.format(control_plane_backends=backends_content)
            # if using the roll_lb method then the backends placeholder will not be there, so preserve the old haproxy.cfg
            lbctl.update_haproxy_config(content)
            lbctl.reload_haproxy()
