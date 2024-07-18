import os
import urllib3

from kp import util
from kp import config
from kp.util import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             CreateControlPlaneCmd(),
                             DeleteControlPlaneCmd(),
                             ViewKubeConfigCmd(),
                             SaveKubeConfigCmd(),
                             CopyKubeCertsCmd(),
                             JoinControlPlaneCmd(),
                             EtcdctlMemberListCmd(),
                             EtcdctlEndpointStatusClusterCmd(),
                             EtcdctlMemberRemoveCmd(),
                             EtcdctlSnapshotSaveCmd(),
                             BackupCmd(),
                         ],
                         aliases=["ctlpl", "plane"])


class CreateControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create", aliases=["add"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=4)
        self.parser.add_argument("--vm-mem", type=int, default=8192)
        self.parser.add_argument("--vm-disk", type=str, default="20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)
        self.parser.add_argument("--vm-containerd-config", type=str, required=True)

        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        vmid = self.parsed_args.vmid
        template_id = self.parsed_args.template_id
        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(vmid)
        vm_cores = self.parsed_args.vm_cores
        vm_mem = self.parsed_args.vm_mem
        vm_disk_size = self.parsed_args.vm_disk
        vm_username = self.parsed_args.vm_username
        vm_password = self.parsed_args.vm_password
        vm_network = self.parsed_args.vm_net
        vm_ip = self.parsed_args.vm_ip
        vm_start_on_boot = self.parsed_args.vm_start_on_boot
        r = PveApi.describe_network(api, node, vm_network)
        network_gw_ip = str(ipaddress.IPv4Interface(r["cidr"]).ip) \
            or r["address"]

        vm_userdata = self.parsed_args.vm_userdata
        vm_containerd_config = self.parsed_args.vm_containerd_config

        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

        PveApi.update_config(api, node, vmid,
                             name=new_vm_name,
                             cpu="cputype=host",
                             cores=vm_cores,
                             memory=vm_mem,
                             agent="enabled=1,fstrim_cloned_disks=1",
                             ciuser=vm_username,
                             cipassword=vm_password,
                             net0=f"virtio,bridge={vm_network}",
                             ipconfig0=f"ip={vm_ip}/24,gw={network_gw_ip}",
                             sshkeys=util.Proxmox.encode_sshkeys(cfg.vm_ssh_keys),
                             onboot=vm_start_on_boot,
                             tags=";".join([config.Tag.kp]),
                             )
        PveApi.resize_disk(api, node, vmid, "scsi0", vm_disk_size)

        PveApi.startup(api, node, vmid)
        PveApi.wait_for_guestagent(api, node, vmid)
        PveApi.wait_for_cloudinit(api, node, vmid)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, vmid, userdata_location, f.read())
        PveApi.exec(api, node, vmid, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, vmid, userdata_location)

        VmService.update_containerd_config(api, node, vmid, vm_containerd_config)
        VmService.restart_containerd(api, node, vmid)

        ControlPlaneService.init(api,
                                 node,
                                 vmid,
                                 control_plane_endpoint=vm_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return vmid


class DeleteControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete", aliases=["remove", "rm"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        vm_id = self.parsed_args.vmid
        util.log.info("vm_id", vm_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        VmService.kubeadm_reset(api, node, vm_id)
        PveApi.shutdown(api, node, vm_id)
        PveApi.wait_for_shutdown(api, node, vm_id)
        PveApi.delete_vm(api, node, vm_id)


class ViewKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("view-kubeconfig", aliases=["cat-kubeconfig"])

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")

    def run(self):
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        _, stdout, _ = ControlPlaneService.cat_kubeconfig(
            api, node, vm_id, filepath)
        print(stdout)


class SaveKubeConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("save-kubeconfig")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("-f",
                                 "--file-path",
                                 default="/etc/kubernetes/admin.conf")
        self.parser.add_argument("-o",
                                 "--output",
                                 default="~/.kube/config")

    def run(self):
        args = self.parsed_args
        vm_id = args.vmid
        filepath = args.file_path
        output = args.output
        urllib3.disable_warnings()
        util.log.info("vm_id", vm_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        _, stdout, _ = ControlPlaneService.cat_kubeconfig(
            api, node, vm_id, filepath)
        with open(output, "w") as f:
            f.write(stdout)


class CopyKubeCertsCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("copy-certs")

    def setup(self):
        self.parser.add_argument("src_id", type=int)
        self.parser.add_argument("dest_id", type=int)

    def run(self):
        args = self.parsed_args
        src_id = args.src_id
        dest_id = args.dest_id
        urllib3.disable_warnings()
        util.log.info("src", src_id, "dest", dest_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ControlPlaneService.ensure_cert_dirs(api, node, dest_id)
        ControlPlaneService.copy_kube_certs(api, node, src_id, dest_id)


class JoinControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("join")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        util.log.info("dad", dad_id, "child", child_id)

        ControlPlaneService.ensure_cert_dirs(api, node, child_id)
        ControlPlaneService.copy_kube_certs(api, node, dad_id, child_id)
        join_cmd = ControlPlaneService.create_join_command(api,
                                                           node,
                                                           dad_id,
                                                           is_control_plane=True)
        PveApi.exec(api, node, child_id, join_cmd)


class EtcdctlMemberListCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("etcdctl-member-list")

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


class EtcdctlEndpointStatusClusterCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("etcdctl-endpoint-status-cluster")

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


class EtcdctlMemberRemoveCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("etcdctl-member-remove", aliases=["etcdctl-member-rm"])

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


class EtcdctlSnapshotSaveCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("etcdctl-snapshot-save")

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


class BackupCmd(Cmd):
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
        PveApi.exec(api, node, vmid, cmd, interval_check=3)
        cmd = f"cp -r /etc/kubernetes/pki {backup_dir}"
        PveApi.exec(api, node, vmid, cmd, interval_check=3)
        cmd = f"cp -r /var/lib/etcd/ {backup_dir}"
        PveApi.exec(api, node, vmid, cmd, interval_check=3)
