import os
import urllib3
import ipaddress

from kp import util
from kp import config
from kp.util import Cmd
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.client.pve import PveApi
from kp.cmd.etcd.etcdctl import EtcdctlCmd
from kp.cmd.v2.plane import V2Cmd


class ControlPlaneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("control-plane",
                         childs=[
                             CreateStandaloneCmd(),
                             DeleteStandaloneCmd(),
                             ViewKubeConfigCmd(),
                             SaveKubeConfigCmd(),
                             CopyKubeCertsCmd(),
                             JoinCmd(),
                             EtcdctlCmd(),
                             HotBackupCmd(),
                             BackupCertsCmd(),
                             RestoreDadCmd(),
                             InitDadCmd(),
                             CreateChildCmd(),
                             CreateDadCmd(),
                             DeleteChildCmd(),
                             UpgradeFirstChildCmd(),
                             UpgradeSecondChildCmd(),
                             V2Cmd(),
                             CreateJoinCmd(),
                         ],
                         aliases=["plane"])


class CreateChildCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-child")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=2)
        self.parser.add_argument("--vm-mem", type=int, default=4096)
        self.parser.add_argument("--vm-disk", type=str, default="+10G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        template_id = self.parsed_args.template_id
        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(child_id)
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

        PveApi.clone(api, node, template_id, child_id)
        PveApi.update_config(api, node, child_id,
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
        PveApi.resize_disk(api, node, child_id, "scsi0", vm_disk_size)

        PveApi.startup(api, node, child_id)
        PveApi.wait_for_guestagent(api, node, child_id)
        PveApi.wait_for_cloudinit(api, node, child_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, child_id, userdata_location, f.read())
        PveApi.exec(api, node, child_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, child_id, userdata_location)

        VmService.update_containerd_config(api, node, child_id)
        VmService.restart_containerd(api, node, child_id)

        ControlPlaneService.ensure_cert_dirs(api, node, child_id)
        ControlPlaneService.copy_kube_certs(api, node, dad_id, child_id)
        join_cmd = ControlPlaneService.create_join_command(api,
                                                           node,
                                                           dad_id,
                                                           is_control_plane=True)
        PveApi.exec(api, node, child_id, join_cmd)


class CreateDadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-dad")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--lb-id", type=int, required=True)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=2)
        self.parser.add_argument("--vm-mem", type=int, default=4096)
        self.parser.add_argument("--vm-disk", type=str, default="+10G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)

        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)

        dad_id = self.parsed_args.dad_id
        lb_id = self.parsed_args.lb_id
        template_id = self.parsed_args.template_id
        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(dad_id)
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

        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr

        PveApi.clone(api, node, template_id, dad_id)
        PveApi.update_config(api, node, dad_id,
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
        PveApi.resize_disk(api, node, dad_id, "scsi0", vm_disk_size)

        PveApi.startup(api, node, dad_id)
        PveApi.wait_for_guestagent(api, node, dad_id)
        PveApi.wait_for_cloudinit(api, node, dad_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, dad_id, userdata_location, f.read())
        PveApi.exec(api, node, dad_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, dad_id, userdata_location)

        VmService.update_containerd_config(api, node, dad_id)
        VmService.restart_containerd(api, node, dad_id)
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect control_plane_endpoint")
        lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        ControlPlaneService.init(api,
                                 node,
                                 dad_id,
                                 control_plane_endpoint=lb_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return dad_id


class DeleteChildCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete-child", aliases=["remove-child", "rm-child"])

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        util.log.info("dad_id", dad_id, "child_id", child_id)
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        child_vm = PveApi.find_vm_by_id(api, node, child_id)

        ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
        ControlPlaneService.delete_node(api, node, dad_id, child_vm.name)
        VmService.kubeadm_reset(api, node, child_id)

        PveApi.shutdown(api, node, child_id)
        PveApi.wait_for_shutdown(api, node, child_id)
        PveApi.delete_vm(api, node, child_id)


class InitDadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("init-dad")

    def setup(self):
        self.parser.add_argument("--lb-id", type=int, required=True)
        self.parser.add_argument("--plane-id", type=int, required=True)
        self.parser.add_argument("--pod-cidr", type=str, required=True)
        self.parser.add_argument("--svc-cidr", type=str, required=True)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        lb_id = self.parsed_args.lb_id
        plane_id = self.parsed_args.plane_id
        pod_cidr = self.parsed_args.pod_cidr
        svc_cidr = self.parsed_args.svc_cidr
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect lb ip for control_plane_endpoint")
        lb_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        ControlPlaneService.init(api,
                                 node,
                                 plane_id,
                                 control_plane_endpoint=lb_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)


class CreateStandaloneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create-standalone")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=2)
        self.parser.add_argument("--vm-mem", type=int, default=4096)
        self.parser.add_argument("--vm-disk", type=str, default="+20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)

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

        VmService.update_containerd_config(api, node, vmid)
        VmService.restart_containerd(api, node, vmid)

        ControlPlaneService.init(api,
                                 node,
                                 vmid,
                                 control_plane_endpoint=vm_ip,
                                 pod_cidr=pod_cidr,
                                 svc_cidr=svc_cidr)
        return vmid


class DeleteStandaloneCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("delete-standalone", aliases=["remove-standalone", "rm-standalone"])

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
        vm_id = self.parsed_args.vmid
        filepath = self.parsed_args.file_path
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
        vm_id = self.parsed_args.vmid
        filepath = self.parsed_args.file_path
        output = self.parsed_args.output
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
        src_id = self.parsed_args.src_id
        dest_id = self.parsed_args.dest_id
        urllib3.disable_warnings()
        util.log.info("src", src_id, "dest", dest_id)
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        ControlPlaneService.ensure_cert_dirs(api, node, dest_id)
        ControlPlaneService.copy_kube_certs(api, node, src_id, dest_id)


class JoinCmd(Cmd):

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


class HotBackupCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("hot-backup")

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


class BackupCertsCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("backup-certs")

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


class RestoreDadCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("restore-dad")

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


class UpgradeFirstChildCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("upgrade-first-child")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)
        self.parser.add_argument("--kubernetes-semver", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        kubernetes_version_minor = ".".join(self.parsed_args.kubernetes_semver.split(".")[0:2])
        kubernetes_version_patch = ".".join(self.parsed_args.kubernetes_semver.split(".")[0:3])

        child_vm = PveApi.find_vm_by_id(api, node, child_id)

        vm_userdata = "/usr/local/bin/upgrade.sh"
        tmpl = config.UPGRADE_PLANE_SCRIPT
        userdata_content = tmpl.format(kubernetes_version_minor=kubernetes_version_minor,
                                       kubernetes_version_patch=kubernetes_version_patch)
        PveApi.write_file(api, node, child_id, vm_userdata, userdata_content)
        PveApi.exec(api, node, child_id, f"chmod +x {vm_userdata}")
        PveApi.exec(api, node, child_id, vm_userdata)
        PveApi.exec(api, node, child_id, "sudo kubeadm upgrade plan".split())
        PveApi.exec(api, node, child_id, f"sudo kubeadm upgrade apply v{kubernetes_version_patch}".split())

        ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
        """
        # NOTE: with quote at package version will not work
        # Eg: apt install -y kubelet="1.29.6-*"
            2024-07-16 00:18:22 [DEBUG] pve-cobi 128 exec 333843 stderr
            E: Version '"1.29.6-*"' for 'kubelet' was not found
            E: Version '"1.29.6-*"' for 'kubectl' was not found
        # I think is because of shell text processing
        """
        cmd = f"apt install -y kubelet={kubernetes_version_patch}-* kubectl={kubernetes_version_patch}-*".split()
        PveApi.exec(api, node, child_id, cmd)
        VmService.systemctl_daemon_reload(api, node, child_id)
        VmService.restart_kubelet(api, node, child_id)
        ControlPlaneService.uncordon_node(api, node, dad_id, child_vm.name)


class UpgradeSecondChildCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("upgrade-second-child")

    def setup(self):
        self.parser.add_argument("--dad-id", type=int, required=True)
        self.parser.add_argument("--child-id", type=int, required=True)
        self.parser.add_argument("--kubernetes-semver", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        dad_id = self.parsed_args.dad_id
        child_id = self.parsed_args.child_id
        kubernetes_version_minor = ".".join(self.parsed_args.kubernetes_semver.split(".")[0:2])
        kubernetes_version_patch = ".".join(self.parsed_args.kubernetes_semver.split(".")[0:3])

        child_vm = PveApi.find_vm_by_id(api, node, child_id)

        vm_userdata = "/usr/local/bin/upgrade.sh"
        tmpl = config.UPGRADE_PLANE_SCRIPT
        userdata_content = tmpl.format(kubernetes_version_minor=kubernetes_version_minor,
                                       kubernetes_version_patch=kubernetes_version_patch)
        PveApi.write_file(api, node, child_id, vm_userdata, userdata_content)
        PveApi.exec(api, node, child_id, f"chmod +x {vm_userdata}")
        PveApi.exec(api, node, child_id, vm_userdata)
        PveApi.exec(api, node, child_id, f"sudo kubeadm upgrade node".split())  # only line that diff from UpgradeFirstChildCmd

        ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
        """
        # NOTE: with quote at package version will not work
        # Eg: apt install -y kubelet="1.29.6-*"
            2024-07-16 00:18:22 [DEBUG] pve-cobi 128 exec 333843 stderr
            E: Version '"1.29.6-*"' for 'kubelet' was not found
            E: Version '"1.29.6-*"' for 'kubectl' was not found
        # I think is because of shell text processing
        """
        cmd = f"apt install -y kubelet={kubernetes_version_patch}-* kubectl={kubernetes_version_patch}-*".split()
        PveApi.exec(api, node, child_id, cmd)
        VmService.systemctl_daemon_reload(api, node, child_id)
        VmService.restart_kubelet(api, node, child_id)
        ControlPlaneService.uncordon_node(api, node, dad_id, child_vm.name)


class CreateJoinCmd(Cmd):
    def __init__(self) -> None:
        super().__init__("create-join-command")

    def setup(self):
        self.parser.add_argument("vmid", type=int)

    def run(self):
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vmid = self.parsed_args.vmid
        util.log.info("vmid", vmid, "create-join-token")
        ControlPlaneService.create_join_command(api, node, vmid)
