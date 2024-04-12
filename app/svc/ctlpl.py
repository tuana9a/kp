import os
import ipaddress

from app.ctler.node import NodeController
from app.logger import Logger
from app import util
from app.error import *


class ControlPlaneService:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

    def copy_kube_certs(self,
                        source_id,
                        dest_id,
                        certs=[
                            "/etc/kubernetes/pki/ca.crt",
                            "/etc/kubernetes/pki/ca.key",
                            "/etc/kubernetes/pki/sa.key",
                            "/etc/kubernetes/pki/sa.pub",
                            "/etc/kubernetes/pki/front-proxy-ca.crt",
                            "/etc/kubernetes/pki/front-proxy-ca.key",
                            "/etc/kubernetes/pki/etcd/ca.crt",
                            "/etc/kubernetes/pki/etcd/ca.key",
                        ]):
        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        nodectl = self.nodectl
        log = self.log
        sourcectl = nodectl.vmctl(source_id)
        destctl = nodectl.vmctl(dest_id)

        for cert in certs:
            r = sourcectl.read_file(cert)
            content = r["content"]
            # TODO: check truncated content https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
            r = destctl.write_file(cert, content)

    def create_control_plane(self,
                             vm_network_name,
                             vm_template_id: int,
                             install_containerd_filepath: str,
                             install_kube_filepath: str,
                             containerd_config_filepath: str,
                             pod_cidr,
                             svc_cidr=None,
                             preserved_ips=[],
                             vm_id_range=[0, 9999],
                             vm_core_count=4,
                             vm_memory=8192,
                             vm_disk_size="20G",
                             vm_name_prefix="i-",
                             vm_username="u",
                             vm_password="1",
                             vm_ssh_keys=None,
                             apiserver_endpoint=None,
                             cni_manifest_file=None,
                             control_plane_vm_id=None,
                             load_balancer_vm_id=None,
                             vm_start_on_boot=1,
                             **kwargs):
        nodectl = self.nodectl
        log = self.log

        is_multiple_control_planes = False
        if load_balancer_vm_id:
            is_multiple_control_planes = True

        r = nodectl.describe_network(vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for ip in vm_network.hosts():
            ip_pool.append(str(ip))
        preserved_ips.append(network_gw_ip)
        log.debug("preserved_ips", preserved_ips)

        new_vm_id = nodectl.new_vm_id(vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(ip_pool, preserved_ips)
        new_vm_name = f"{vm_name_prefix}{new_vm_id}"

        log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        nodectl.clone(vm_template_id, new_vm_id)

        ctlplvmctl = nodectl.ctlplvmctl(new_vm_id)
        ctlplvmctl.update_config(
            name=new_vm_name,
            cpu="cputype=host",
            cores=vm_core_count,
            memory=vm_memory,
            agent="enabled=1,fstrim_cloned_disks=1",
            ciuser=vm_username,
            cipassword=vm_password,
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            onboot=vm_start_on_boot,
        )
        ctlplvmctl.resize_disk("scsi0", vm_disk_size)

        ctlplvmctl.startup()
        ctlplvmctl.wait_for_guest_agent()
        log.info("started vm", new_vm_id)

        ctlplvmctl.wait_for_cloud_init()
        log.info("waited for cloud-init", new_vm_id)

        vm_install_containerd_location = "/usr/local/bin/install-containerd.sh"
        with open(install_containerd_filepath, "r") as f:
            ctlplvmctl.write_file(vm_install_containerd_location, f.read())
        ctlplvmctl.exec(f"chmod +x {vm_install_containerd_location}")
        ctlplvmctl.exec(vm_install_containerd_location)

        with open(containerd_config_filepath) as f:
            ctlplvmctl.write_file("/etc/containerd/config.toml", f.read())
        ctlplvmctl.exec("systemctl restart containerd")

        vm_install_kube_location = "/usr/local/bin/install-kube.sh"
        with open(install_kube_filepath, "r") as f:
            ctlplvmctl.write_file(vm_install_kube_location, f.read())
        ctlplvmctl.exec(f"chmod +x {vm_install_kube_location}")
        ctlplvmctl.exec(vm_install_kube_location)

        # SECTION: standalone control plane
        if not is_multiple_control_planes:
            exitcode, _, _ = ctlplvmctl.kubeadm().init(
                control_plane_endpoint=new_vm_ip,
                pod_cidr=pod_cidr,
                svc_cidr=svc_cidr)

            if not cni_manifest_file:
                log.info("skip apply cni step")
                return new_vm_id

            cni_filepath = "/root/cni.yaml"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                ctlplvmctl.write_file(cni_filepath, f.read())
                ctlplvmctl.apply_file(cni_filepath)
            return new_vm_id

        # SECTION: stacked control plane
        lbctl = nodectl.lbctl(load_balancer_vm_id)
        exitcode, _, stderr = lbctl.add_backend("control-plane", new_vm_id,
                                                f"{new_vm_ip}:6443")
        if exitcode != 0:
            log.error(stderr)
            raise Exception("some thing wrong with add_backend")
        lbctl.reload_haproxy()

        # No previous control plane, init a new one
        if not control_plane_vm_id:
            control_plane_endpoint = apiserver_endpoint
            if not control_plane_endpoint:
                lb_config = lbctl.current_config()
                lb_ifconfig0 = lb_config.get("ipconfig0", None)
                if not lb_ifconfig0:
                    raise Exception(
                        "can not detect the control_plane_endpoint")
                vm_ip = util.ProxmoxUtil.extract_ip(lb_ifconfig0)
                control_plane_endpoint = vm_ip
            exitcode, _, _ = ctlplvmctl.kubeadm().init(
                control_plane_endpoint=control_plane_endpoint,
                pod_cidr=pod_cidr,
                svc_cidr=svc_cidr)

            if not cni_manifest_file:
                log.info("skip ini cni step")
                return new_vm_id

            cni_filepath = "/root/cni.yaml"
            with open(cni_manifest_file, "r", encoding="utf-8") as f:
                ctlplvmctl.write_file(cni_filepath, f.read())
                ctlplvmctl.apply_file(cni_filepath)
            return new_vm_id

        # There are previous control plane prepare new control plane
        ctlplvmctl.ensure_cert_dirs()
        self.copy_kube_certs(control_plane_vm_id, new_vm_id)
        existed_ctlplvmctl = nodectl.ctlplvmctl(control_plane_vm_id)
        join_cmd = existed_ctlplvmctl.kubeadm().create_join_command(
            is_control_plane=True)
        log.info("join_cmd", " ".join(join_cmd))
        ctlplvmctl.exec(join_cmd, timeout=20 * 60)
        return new_vm_id

    def delete_control_plane(self,
                             vm_id,
                             load_balancer_vm_id=None,
                             control_plane_vm_id=None,
                             **kwargs):
        nodectl = self.nodectl
        log = self.log
        vm = nodectl.find_vm(vm_id)
        vm_name = vm["name"]
        ctlplvmctl = nodectl.ctlplvmctl(vm_id)
        # kubeadm reset is needed when deploying stacked control plane
        # https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-reset/#reset-workflow
        # Remove the control plane with etcd will avoid this error
        # https://serverfault.com/questions/1029654/deleting-a-control-node-from-the-cluster-kills-the-apiserver
        try:
            ctlplvmctl.kubeadm().reset()
        except Exception as err:
            log.error(err)

        if load_balancer_vm_id:
            if control_plane_vm_id:
                nodectl.ctlplvmctl(control_plane_vm_id).delete_node(vm_name)
            lbctl = nodectl.lbctl(load_balancer_vm_id)
            exitcode, stdout, stderr = lbctl.rm_backend("control-plane", vm_id)
            if exitcode != 0:
                log.error(str(stderr))
            lbctl.reload_haproxy()

        ctlplvmctl.shutdown()
        ctlplvmctl.wait_for_shutdown()
        ctlplvmctl.delete()
        return vm_id
