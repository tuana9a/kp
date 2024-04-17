import os
import urllib3

from app.model.plane import ControlPlaneVm
from app.model.vm import Vm
from cli.core import Cmd
from app.model.pve import PveNode
from app.service.plane import ControlPlaneService
from app import util
from app import config
from app.model.lb import LbVm


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
                         aliases=["ctlpl"])


class CreateControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create", aliases=["add"])

    def _run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        service = ControlPlaneService(nodectl)
        service.create_control_plane(cfg)


class DeleteControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def _setup(self):
        self.parser.add_argument("vmid", type=int)

    def _run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        args = self.parsed_args
        vm_id = args.vmid or os.getenv("VMID")
        util.log.info("vm_id", vm_id)
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        clusterctl = ControlPlaneService(nodectl)
        clusterctl.delete_control_plane(cfg, vm_id)


class KubeConfigCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("kubeconfig", childs=[
            ViewKubeConfigCmd(),
            SaveKubeConfigCmd(),
        ])


class ViewKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("view", aliases=["cat"])

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
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        ctlplvmctl = ControlPlaneVm(nodectl.api, nodectl.node, vm_id)
        _, stdout, _ = ctlplvmctl.cat_kubeconfig(filepath)
        print(stdout)


class SaveKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("save")

    def _setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")
        self.parser.add_argument("-o",
                                 "--output",
                                 default="~/.kube/config")

    def _run(self):
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
        output = args.output
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        ctlplvmctl = ControlPlaneVm(nodectl.api, nodectl.node, vm_id)
        _, stdout, _ = ctlplvmctl.cat_kubeconfig(filepath)
        with open(output, "w") as f:
            f.write(stdout)


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
        util.log.info("src", source_id, "dest", dest_id)
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        ControlPlaneVm(nodectl.api, nodectl.node, dest_id).ensure_cert_dirs()
        service = ControlPlaneService(nodectl)
        service.copy_kube_certs(source_id, dest_id)


class JoinControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def _setup(self):
        self.parser.add_argument("ctlplids", nargs="+", type=int)

    def _run(self):
        urllib3.disable_warnings()
        args = self.parsed_args
        control_plane_ids = args.ctlplids
        child_ids_set = set(control_plane_ids)
        cfg = util.load_config()
        proxmox_node = cfg.proxmox_node
        vm_id_range = cfg.vm_id_range
        proxmox_client = util.Proxmox.create_api_client(cfg)
        nodectl = PveNode(proxmox_client, proxmox_node)
        service = ControlPlaneService(nodectl)
        ctlpl_list = nodectl.detect_control_planes(vm_id_range=vm_id_range)

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

        lb_vm_list = nodectl.detect_load_balancers(vm_id_range)

        if not len(lb_vm_list):
            util.log.info("can't not find load balancers")
            return

        lb_vm_id = lb_vm_list[0].vmid
        lbctl = LbVm(nodectl.api, nodectl.node, lb_vm_id)
        dadctl = ControlPlaneVm(nodectl.api, nodectl.node, control_plane_id)
        join_cmd = dadctl.create_join_command(is_control_plane=True)

        # EXPLAIN: need to join and update the tags before detect control plane
        # by tag
        for id in control_plane_ids:
            ctlplvmctl = ControlPlaneVm(nodectl.api, nodectl.node, id)
            ctlplvmctl.ensure_cert_dirs()
            service.copy_kube_certs(control_plane_id, id)
            ctlplvmctl.exec(join_cmd)
            ctlplvmctl.update_config(tags=[config.Tag.ctlpl, config.Tag.kp])

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
