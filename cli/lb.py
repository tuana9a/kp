import urllib3

from app.model.vm import Vm
from cli.core import Cmd
from app.model.pve import PveNode
from app.service.lb import LbService
from app import util
from app import config
from app.model.lb import LbVm


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
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        service = LbService(nodectl)
        service.create_lb(cfg)


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
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        lbctl = LbVm(nodectl.api, nodectl.node, vm_id)
        with open(path, "r", encoding="utf-8") as f:
            lbctl.write_file(config.HAPROXY_CONFIG_LOCATION, f.read())
        lbctl.reload_haproxy()


class UpdateConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("update-config")

    def _run(self):
        args = self.parsed_args
        urllib3.disable_warnings()
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        vm_id_range = cfg.vm_id_range
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        lb_vm_list = nodectl.detect_load_balancers(vm_id_range=vm_id_range)
        if not len(lb_vm_list):
            util.log.info("can't not find load balancers")
        vm_id = lb_vm_list[0].vmid
        lbctl = LbVm(nodectl.api, nodectl.node, vm_id)
        with open(cfg.haproxy_cfg, "r", encoding="utf8") as f:
            content = f.read()
            ctlpl_list = nodectl.detect_control_planes(vm_id_range=vm_id_range)
            backends = []
            for x in ctlpl_list:
                vmid = x.vmid
                ifconfig0 = Vm(nodectl.api, nodectl.node,
                               vmid).current_config().ifconfig(0)
                if ifconfig0:
                    vmip = util.Proxmox.extract_ip(ifconfig0)
                    backends.append([vmid, vmip])
            backends_content = util.Haproxy.render_backends_config(backends)
            content = content.format(control_plane_backends=backends_content)
            # if using the roll_lb method then the backends placeholder will
            # not be there, so preserve the old haproxy.cfg
            lbctl.update_haproxy_config(content)
            lbctl.reload_haproxy()
