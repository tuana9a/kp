import os
import urllib3
import ipaddress

from kp import util
from kp import config
from kp.model import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class HotRecoveryCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("hot-recovery",
                         childs=[
                             HotBackupCmd(),
                             HotRestoreCmd(),
                         ],
                         aliases=["recovery"])


class HotBackupCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("backup")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("--backup-dir", type=str, default="/root/backup")

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        backup_dir = self.parsed_args.backup_dir
        util.log.info("vmid", vmid, "backup_dir", backup_dir)
        cmd = f"mkdir -p {backup_dir}".split()
        PveApi.exec(api, node, vmid, cmd)
        cmd = f"cp -r /etc/kubernetes/pki {backup_dir}"
        PveApi.exec(api, node, vmid, cmd)
        cmd = f"cp -r /var/lib/etcd/ {backup_dir}"
        PveApi.exec(api, node, vmid, cmd)


class HotRestoreCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("restore")

    def setup(self):
        self.parser.add_argument("--lb-id", type=int, required=True)
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--backup-dir", type=str, default="/root/backup")
        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        cfg = util.load_config()
        lb_id = self.parsed_args.lb_id
        dad_id = self.parsed_args.dad_id
        backup_dir = self.parsed_args.backup_dir
        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

        util.log.info("lb_id", lb_id, "dad_id", dad_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        dad_vm = PveApi.find_vm_by_id(api, node, dad_id)
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect control_plane_endpoint")
        lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        dad_ifconfig0 = PveApi.current_config(api, node, dad_id).ifconfig(0)
        if not dad_ifconfig0:
            raise Exception("can not detect dad ip")
        dad_ip = util.Proxmox.extract_ip(dad_ifconfig0)

        VmService.kubeadm_reset(api, node, dad_id)
        cmd = f"cp -r {backup_dir}/pki/ /etc/kubernetes/"
        PveApi.exec(api, node, dad_id, cmd)

        cmd = f"""/usr/local/bin/etcdutl snapshot restore {backup_dir}/etcd/member/snap/db \
            --name {dad_vm.name} \
            --initial-cluster {dad_vm.name}=https://{dad_ip}:2380 \
            --initial-cluster-token recovery-mode \
            --initial-advertise-peer-urls https://{dad_ip}:2380 \
            --skip-hash-check=true \
            --bump-revision 1000000000 --mark-compacted \
            --data-dir /var/lib/etcd
        """.split()
        PveApi.exec(api, node, dad_id, cmd)

        ControlPlaneService.init(api, node, dad_id, lb_ip,
                                 extra_opts=["--ignore-preflight-errors=DirAvailable--var-lib-etcd"],
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
