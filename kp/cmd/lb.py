import urllib3

from kp.service.vm import VmService
from kp.util import Cmd
from kp.service.pve import PveService
from kp.service.lb import LbService
from kp import util
from kp import config


class LbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("lb",
                         childs=[
                             CreateLbCmd(),
                             CopyConfigCmd(),
                             ReadConfigCmd(),
                             UpdateConfigCmd(),
                         ])


class CreateLbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        LbService.create_lb(api, node, cfg)


class CopyConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-config")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("path", type=str)

    def run(self):
        args = self.parsed_args
        path = args.path
        vm_id = args.vmid
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        with open(path, "r", encoding="utf-8") as f:
            VmService.write_file(
                api,
                node,
                vm_id,
                config.HAPROXY_CONFIG_LOCATION,
                f.read())
        LbService.reload_haproxy(api, node, vm_id)


class UpdateConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("update-config")

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        lb_vm_list = PveService.detect_load_balancers(
            api, node, id_range=cfg.vm_id_range)
        if not len(lb_vm_list):
            util.log.info("can't not find load balancers")
        vm_id = lb_vm_list[0].vmid
        ctlpl_list = PveService.detect_control_planes(
            api, node, id_range=cfg.vm_id_range)
        backends = []
        for x in ctlpl_list:
            vmid = x.vmid
            ifconfig0 = VmService.current_config(api, node, vmid).ifconfig(0)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                backends.append([vmid, vmip])
        backends_content = util.Haproxy.render_backends_config(backends)
        content = config.HAPROXY_CONFIG_TEMPLATE.format(
            control_plane_backends=backends_content)
        # if using the roll_lb method then the backends placeholder will
        # not be there, so preserve the old haproxy.cfg
        LbService.update_haproxy_config(api, node, vm_id, content)
        LbService.reload_haproxy(api, node, vm_id)


class ReadConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("read-config")

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        lb_vm_list = PveService.detect_load_balancers(
            api, node, id_range=cfg.vm_id_range)
        if not len(lb_vm_list):
            util.log.info("can't not find load balancers")
        vm_id = lb_vm_list[0].vmid
        print(LbService.read_haproxy_config(api, node, vm_id)["content"])
