import ipaddress

from typing import List
from proxmoxer import ProxmoxAPI
from kp.service.pve import PveService
from kp import util
from kp.error import *
from kp import config
from kp.service.vm import VmService
from kp.service.lb import LbService
from kp.service.kube import KubeadmService, KubeVmService
from kp.payload import Cfg, VmResponse


class ControlPlaneService:
    @staticmethod
    def drain_node(api: ProxmoxAPI,
                   node: str,
                   vm_id: str,
                   node_name: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION,
                   opts=["--ignore-daemonsets", "--delete-emptydir-data"]):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain",
            node_name, *opts
        ]
        # 30 mins should be enough
        return VmService.exec(
            api,
            node,
            vm_id,
            cmd,
            interval_check=5,
            timeout=30 *
            60)

    @staticmethod
    def delete_node(api: ProxmoxAPI,
                    node: str,
                    vm_id: str,
                    node_name,
                    kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete", "node",
            node_name
        ]
        return VmService.exec(api, node, vm_id, cmd, interval_check=5)

    @staticmethod
    def ensure_cert_dirs(
        api: ProxmoxAPI,
        node: str,
        vm_id: str,
        cert_dirs=[
            "/etc/kubernetes/pki",
            "/etc/kubernetes/pki/etcd"]):
        for d in cert_dirs:
            cmd = ["mkdir", "-p", d]
            VmService.exec(api, node, vm_id, cmd, interval_check=3)

    @staticmethod
    def cat_kubeconfig(
            api: ProxmoxAPI,
            node: str,
            vm_id: str,
            filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = ["cat", filepath]
        return VmService.exec(api, node, vm_id, cmd, interval_check=2)

    @staticmethod
    def apply_file(api: ProxmoxAPI,
                   node: str,
                   vm_id: str,
                   filepath: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = [
            "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}", "-f",
            filepath
        ]
        return VmService.exec(api, node, vm_id, cmd)

    @staticmethod
    def copy_kube_certs(api: ProxmoxAPI,
                        node: str,
                        src_id,
                        dest_id,
                        cert_paths=config.KUBERNETES_CERT_PATHS):
        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        for cert_path in cert_paths:
            r = VmService.read_file(api, node, src_id, cert_path)
            content = r["content"]
            # TODO: check truncated content
            # https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
            r = VmService.write_file(api, node, dest_id, cert_path, content)

    @staticmethod
    def create_control_plane(api: ProxmoxAPI,
                             node: str,
                             cfg: Cfg):
        r = PveService.describe_network(api, node, cfg.vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]

        new_vm_id = PveService.new_vm_id(
            api,
            node,
            id_range=cfg.vm_id_range,
            preserved_ids=cfg.vm_preserved_ids)
        new_vm_ip = PveService.new_vm_ip(
            api,
            node,
            cfg.vm_network_name,
            id_range=cfg.vm_id_range,
            preserved_ips=cfg.vm_preserved_ips)
        new_vm_name = f"{cfg.vm_name_prefix}{new_vm_id}"

        util.log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        PveService.clone(api, node, cfg.vm_template_id, new_vm_id)

        VmService.update_config(api, node, new_vm_id,
                                name=new_vm_name,
                                cpu="cputype=host",
                                cores=cfg.vm_core_count,
                                memory=cfg.vm_memory,
                                agent="enabled=1,fstrim_cloned_disks=1",
                                ciuser=cfg.vm_username,
                                cipassword=cfg.vm_password,
                                net0=f"virtio,bridge={cfg.vm_network_name}",
                                ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
                                sshkeys=util.Proxmox.encode_sshkeys(cfg.vm_ssh_keys),
                                onboot=cfg.vm_start_on_boot,
                                tags=";".join([config.Tag.ctlpl, config.Tag.kp]),
                                )
        VmService.resize_disk(api, node, new_vm_id, "scsi0", cfg.vm_disk_size)

        VmService.startup(api, node, new_vm_id)
        VmService.wait_for_guest_agent(api, node, new_vm_id)
        VmService.wait_for_cloud_init(api, node, new_vm_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(cfg.userdata_control_plane_filepath, "r") as f:
            VmService.write_file(
                api, node, new_vm_id, userdata_location, f.read())
        VmService.exec(api, node, new_vm_id, f"chmod +x {userdata_location}")
        VmService.exec(api, node, new_vm_id, userdata_location)

        with open(cfg.containerd_config_filepath) as f:
            VmService.write_file(
                api,
                node,
                new_vm_id,
                "/etc/containerd/config.toml",
                f.read())
            KubeVmService.restart_containerd(api, node, new_vm_id)
            KubeVmService.restart_kubelet(api, node, new_vm_id)

        existed_lb_vm_id = None
        lb_vm_list: List[VmResponse] = PveService.detect_load_balancers(
            api, node, id_range=cfg.vm_id_range)
        if len(lb_vm_list):
            existed_lb_vm_id = lb_vm_list[0].vmid
            util.log.info("existed_lb_vm_id", existed_lb_vm_id, "AUTO_DETECT")

        is_multiple_control_planes = bool(existed_lb_vm_id)
        util.log.info("is_multiple_control_planes", is_multiple_control_planes)

        # SECTION: standalone control plane
        if not is_multiple_control_planes:
            KubeadmService.init(
                api,
                node,
                new_vm_id,
                control_plane_endpoint=new_vm_ip,
                pod_cidr=cfg.pod_cidr,
                svc_cidr=cfg.svc_cidr)
            return new_vm_id

        # SECTION: stacked control plane
        ctlpl_vm_list: List[VmResponse] = PveService.detect_control_planes(
            api, node, id_range=cfg.vm_id_range)
        existed_ctlpl_vm_id = None
        for ctlpl_vm in ctlpl_vm_list:
            ctlpl_vm_id = ctlpl_vm.vmid
            # NOTE: avoid exist id is the same with newly created one
            if ctlpl_vm_id != new_vm_id:
                existed_ctlpl_vm_id = ctlpl_vm_id
                util.log.info("existed_ctlpl_vm_id", existed_ctlpl_vm_id,
                              "AUTO_DETECT")

        # EXPLAIN: previous control plane existed, joining new control plane
        if existed_ctlpl_vm_id:
            ControlPlaneService.ensure_cert_dirs(api, node, new_vm_id)
            ControlPlaneService.copy_kube_certs(
                api, node, existed_ctlpl_vm_id, new_vm_id)
            join_cmd = KubeadmService.create_join_command(
                api, node, existed_ctlpl_vm_id, is_control_plane=True)
            util.log.info("join_cmd", " ".join(join_cmd))
            VmService.exec(api, node, new_vm_id, join_cmd, timeout=20 * 60)
            return new_vm_id

        # EXPLAIN: previous control plane is not found, init a fresh new
        # control plane
        lb_ifconfig0 = VmService.current_config(
            api, node, existed_lb_vm_id).ifconfig(0)
        if not lb_ifconfig0:
            raise Exception("can not detect control_plane_endpoint")
        vm_ip = util.Proxmox.extract_ip(lb_ifconfig0)
        control_plane_endpoint = vm_ip
        KubeadmService.init(
            api,
            node,
            new_vm_id,
            control_plane_endpoint=control_plane_endpoint,
            pod_cidr=cfg.pod_cidr,
            svc_cidr=cfg.svc_cidr)
        return new_vm_id

    @staticmethod
    def delete_control_plane(api: ProxmoxAPI,
                             node: str,
                             vm_id: str, cfg: Cfg):
        vm_list = PveService.list_vm(api, node, id_range=cfg.vm_id_range)
        vm: VmResponse = util.Proxmox.filter_vm_id(vm_list, vm_id)
        vm_name = vm.name
        # kubeadm reset is needed when deploying stacked control plane
        # https://kubernetes.io/docs/reference/setup-tools/kubeadm/kubeadm-reset/#reset-workflow
        # Remove the control plane with etcd will avoid this error
        # https://serverfault.com/questions/1029654/deleting-a-control-node-from-the-cluster-kills-the-apiserver
        try:
            KubeadmService.reset(api, node, vm_id)
        except Exception as err:
            util.log.error(err)

        lb_vm_list = PveService.detect_load_balancers(
            api, node, id_range=cfg.vm_id_range)
        if len(lb_vm_list):
            existed_lb_vm_id = lb_vm_list[0].vmid

        if not existed_lb_vm_id:
            VmService.shutdown(api, node, vm_id)
            VmService.wait_for_shutdown(api, node, vm_id)
            VmService.delete(api, node, vm_id)
            return

        # find exsited control plane
        existed_ctlpl_vm_id = None
        for x in PveService.detect_control_planes(
                api, node, id_range=cfg.vm_id_range):
            ctlpl_vm_id = x.vmid
            if ctlpl_vm_id != vm_id:
                existed_ctlpl_vm_id = ctlpl_vm_id
                break

        # other control plane existing -> multiple control plane, so remove
        # current one
        if existed_ctlpl_vm_id:
            ControlPlaneService.delete_node(
                api, node, existed_ctlpl_vm_id, vm_name)

        VmService.shutdown(api, node, vm_id)
        VmService.wait_for_shutdown(api, node, vm_id)
        VmService.delete(api, node, vm_id)

        return vm_id
