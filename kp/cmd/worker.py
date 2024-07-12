import os
import urllib3

from kp import util
from kp.util import Cmd
from kp.service.worker import WorkerService
from kp import config
from kp.service.pve import PveService
from kp.service.plane import ControlPlaneService
from kp.service.kube import KubeadmService
from kp.service.vm import VmService


class WorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("worker",
                         childs=[
                             CreateWorkerCmd(),
                             DeleteWorkerCmd(),
                             JoinWorkerCmd(),
                         ],
                         aliases=["wk"])


class CreateWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create", aliases=["add"])

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        WorkerService.create_worker(api, node, cfg)


class DeleteWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        WorkerService.delete_worker(api, node, vm_id, cfg)


class JoinWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def setup(self):
        self.parser.add_argument("workerids", nargs="+")

    def run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        worker_ids = args.workerids
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        control_planes = PveService.detect_control_planes(
            api, node, id_range=cfg.vm_id_range)
        if not len(control_planes):
            util.log.info("can't not find any control planes")
            return
        control_plane_id = control_planes[0].vmid
        util.log.info("ctlpl", control_plane_id, "workers", worker_ids)
        join_cmd = KubeadmService.create_join_command(
            api, node, control_plane_id)
        for vmid in worker_ids:
            VmService.exec(api, node, vmid, join_cmd)
            VmService.update_config(
                api, node, vmid, tags=[
                    config.Tag.wk, config.Tag.kp])
