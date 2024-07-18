import urllib3

from kp import util
from kp.client.pve import PveApi
from kp.util import Cmd


class EtcdctlCmd(Cmd):
    def __init__(self):
        super().__init__("etcdctl", childs=[
            MemberCmd(),
            EndpointCmd(),
            SnapshotCmd(),
        ])


class MemberCmd(Cmd):
    def __init__(self):
        super().__init__("member", childs=[
            MemberListCmd(),
            MemberRemoveCmd(),
        ])


class MemberListCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("list")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        util.log.info("vmid", vmid)
        opts = [
            "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
            "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
            "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
        ]
        cmd = "/usr/local/bin/etcdctl member list -w table".split()
        cmd.extend(opts)
        PveApi.exec(api, node, vmid, cmd, interval_check=3)


class MemberRemoveCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("remove", aliases=["rm"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("member_id", type=str)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        member_id = self.parsed_args.member_id
        util.log.info("vmid", vmid, "member_id", member_id)
        opts = [
            "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
            "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
            "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
        ]
        cmd = f"/usr/local/bin/etcdctl member remove {member_id}".split()
        cmd.extend(opts)
        PveApi.exec(api, node, vmid, cmd, interval_check=3)


class EndpointCmd(Cmd):
    def __init__(self):
        super().__init__("endpoint", childs=[
            EndpointStatusCmd(),
        ])


class EndpointStatusCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("status")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        util.log.info("vmid", vmid)
        opts = [
            "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
            "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
            "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
        ]
        cmd = "/usr/local/bin/etcdctl endpoint status --cluster -w table".split()
        cmd.extend(opts)
        PveApi.exec(api, node, vmid, cmd, interval_check=3)


class SnapshotCmd(Cmd):
    def __init__(self):
        super().__init__("snapshot", childs=[
            SnapshotSaveCmd(),
        ])


class SnapshotSaveCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("save")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("--backup-dir", type=str, default="/root/backup")

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        backup_dir = self.parsed_args.backup_dir
        util.log.info("vmid", vmid, "backup_dir", backup_dir)
        opts = [
            "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
            "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
            "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
        ]
        cmd = f"mkdir -p {backup_dir}".split()
        PveApi.exec(api, node, vmid, cmd, interval_check=3)
        cmd = f"/usr/local/bin/etcdctl snapshot save {backup_dir}/snapshot.db".split()
        cmd.extend(opts)
        PveApi.exec(api, node, vmid, cmd, interval_check=3)
