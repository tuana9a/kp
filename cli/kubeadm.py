import urllib3

from app import util
from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app import config


class KubeadmCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("kubeadm", childs=[
            ResetKubeCmd(),
        ], aliases=["adm"])


class ResetKubeCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("reset")

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        args = self.parsed_args
        vm_id = args.vmid
        urllib3.disable_warnings()
        log = Logger.from_env()
        log.info("vm_id", vm_id)
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        vmctl = nodectl.kubeadmctl(vm_id)
        vm_current_config = vmctl.current_config()
        vm_name = vm_current_config["name"]
        ctlpl_list = nodectl.detect_control_planes(
            vm_id_range=cfg["vm_id_range"])

        if len(ctlpl_list):
            ctlpl_vm_id = ctlpl_list[0]["vmid"]
            ctlplvmctl = nodectl.ctlplvmctl(ctlpl_vm_id)
            ctlplvmctl.drain_node(vm_name)
            ctlplvmctl.delete_node(vm_name)

        # run the drain before the reset or pod can't not be killed
        vmctl.kubeadm.reset()
        vmctl.update_config(tags=[config.Tag.kp])

        lb_vm_list = nodectl.detect_load_balancers(cfg["vm_id_range"])
        if len(lb_vm_list):
            lb_vm_id = lb_vm_list[0]["vmid"]
            lbctl = nodectl.lbctl(lb_vm_id)
            with open(cfg["haproxy_cfg"], "r", encoding="utf8") as f:
                content = f.read()
                ctlpl_list = nodectl.detect_control_planes(
                    vm_id_range=cfg["vm_id_range"])
                backends_content = util.Haproxy.render_backends_config(
                    ctlpl_list)
                content = content.format(
                    control_plane_backends=backends_content)
                # if using the roll_lb method then the backends placeholder will not be there, so preserve the old haproxy.cfg
                lbctl.update_haproxy_config(content)
                lbctl.reload_haproxy()
