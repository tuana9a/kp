import urllib3

from cli.core import Cmd
from app.config import load_config
from app.logger import Logger
from app.controller.node import NodeController
from app.service.lb import LbService
from app import util
from app import config


class LbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("lb",
                         childs=[
                             CreateLbCmd(),
                             CopyConfigCmd(),
                             UpdateConfigCmd(),
                         ])


class CreateLbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def _run(self):
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        service = LbService(nodectl, log=log)
        service.create_lb(**cfg)


class CopyConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-config")

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("path", type=str)

    def _run(self):
        args = self.parsed_args
        path = args.path
        vm_id = args.vmid
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        lbctl = nodectl.lbctl(vm_id)
        with open(path, "r", encoding="utf-8") as f:
            lbctl.write_file(config.HAPROXY_CONFIG_LOCATION, f.read())
        lbctl.reload_haproxy()


class UpdateConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("update-config")

    def _run(self):
        args = self.parsed_args
        urllib3.disable_warnings()
        log = Logger.from_env()
        cfg = load_config(log=log)
        proxmox_node = cfg["proxmox_node"]
        proxmox_client = NodeController.create_proxmox_client(**cfg, log=log)
        nodectl = NodeController(proxmox_client, proxmox_node, log=log)
        lb_vm_list = nodectl.detect_load_balancers(cfg["vm_id_range"])
        if not len(lb_vm_list):
            log.info("can't not find load balancers")
        vm_id = lb_vm_list[0]["vmid"]
        lbctl = nodectl.lbctl(vm_id)
        with open(cfg["haproxy_cfg"], "r", encoding="utf8") as f:
            content = f.read()
            ctlpl_list = nodectl.detect_control_planes(
                vm_id_range=cfg["vm_id_range"])
            backends_content = util.Haproxy.render_backends_config(ctlpl_list)
            content = content.format(control_plane_backends=backends_content)
            # if using the roll_lb method then the backends placeholder will not be there, so preserve the old haproxy.cfg
            lbctl.update_haproxy_config(content)
            lbctl.reload_haproxy()
