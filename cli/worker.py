import os
import urllib3

from app import util
from cli.core import Cmd
from app.service.worker import WorkerService
from app import config
from app.model.pve import PveNode
from app.model.worker import WorkerVm
from app.model.plane import ControlPlaneVm


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

    def _run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        service = WorkerService(nodectl)
        service.create_worker(cfg)


class DeleteWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        service = WorkerService(nodectl)
        service.delete_worker(cfg, vm_id)


class JoinWorkerCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def _setup(self):
        self.parser.add_argument("workerids", nargs="+")

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        worker_ids = args.workerids
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        vm_id_range = cfg.vm_id_range
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        control_planes = nodectl.detect_control_planes(vm_id_range=vm_id_range)
        if not len(control_planes):
            util.log.info("can't not find any control planes")
            return
        control_plane_id = control_planes[0].vmid
        util.log.info("ctlpl", control_plane_id, "workers", worker_ids)
        ctlctl = ControlPlaneVm(nodectl.api, nodectl.node, control_plane_id)
        join_cmd = ctlctl.create_join_command()
        for id in worker_ids:
            wkctl = WorkerVm(nodectl.api, nodectl.node, id)
            wkctl.exec(join_cmd)
            wkctl.update_config(tags=[config.Tag.wk, config.Tag.kp])
