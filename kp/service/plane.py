import ipaddress

from typing import List
from proxmoxer import ProxmoxAPI
from kp.client.pve import PveApi
from kp import util
from kp.error import *
from kp import config
from kp.service.vm import VmService
from kp.service.lb import LbService
from kp.payload import Cfg, VmResponse


class ControlPlaneService:
    @staticmethod
    def init(api: ProxmoxAPI,
             node: str,
             vm_id: str,
             control_plane_endpoint,
             pod_cidr,
             svc_cidr,
             timeout=10 * 60,
             extra_opts=[]):
        cmd = [
            "kubeadm",
            "init",
            f"--control-plane-endpoint={control_plane_endpoint}",
            f"--pod-network-cidr={pod_cidr}",
            f"--service-cidr={svc_cidr}",
        ]
        cmd.extend(extra_opts)
        return PveApi.exec(api, node, vm_id, cmd, timeout=timeout)

    @staticmethod
    def create_join_command(api: ProxmoxAPI,
                            node: str,
                            vm_id: str,
                            cmd=["kubeadm", "token", "create",
                                 "--print-join-command"],
                            is_control_plane=False,
                            timeout=config.TIMEOUT_IN_SECONDS,
                            interval_check=3):
        exitcode, stdout, stderr = PveApi.exec(api, node, vm_id, cmd,
                                               timeout=timeout, interval_check=interval_check)
        if exitcode != 0:
            raise CreateJoinCmdFailed(stderr)
        join_cmd = stdout.split()
        if is_control_plane:
            join_cmd.append("--control-plane")
        return join_cmd

    @staticmethod
    def drain_node(api: ProxmoxAPI,
                   node: str,
                   vm_id: str,
                   node_name: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION,
                   opts=["--ignore-daemonsets",
                         "--delete-emptydir-data",
                         "--disable-eviction=true"]):
        cmd = ["kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain", node_name]
        cmd.extend(opts)
        # 30 mins should be enough
        return PveApi.exec(api, node, vm_id, cmd,
                           interval_check=5,
                           timeout=30 * 60)

    @staticmethod
    def uncordon_node(api: ProxmoxAPI,
                      node: str,
                      vm_id: str,
                      node_name: str,
                      kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION,
                      opts=[]):
        cmd = ["kubectl", f"--kubeconfig={kubeconfig_filepath}", "uncordon", node_name]
        cmd.extend(opts)
        return PveApi.exec(api, node, vm_id, cmd,
                           interval_check=5,
                           timeout=5 * 60)

    @staticmethod
    def delete_node(api: ProxmoxAPI,
                    node: str,
                    vm_id: str,
                    node_name,
                    kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = ["kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete", "node", node_name]
        return PveApi.exec(api, node, vm_id, cmd, interval_check=5)

    @staticmethod
    def ensure_cert_dirs(api: ProxmoxAPI,
                         node: str,
                         vm_id: str,
                         cert_dirs=[
            "/etc/kubernetes/pki",
            "/etc/kubernetes/pki/etcd",
                             ]):
        for d in cert_dirs:
            cmd = ["mkdir", "-p", d]
            PveApi.exec(api, node, vm_id, cmd, interval_check=2)

    @staticmethod
    def cat_kubeconfig(api: ProxmoxAPI,
                       node: str,
                       vm_id: str,
                       filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = ["cat", filepath]
        return PveApi.exec(api, node, vm_id, cmd, interval_check=2)

    @staticmethod
    def apply_file(api: ProxmoxAPI,
                   node: str,
                   vm_id: str,
                   filepath: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = ["kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}", "-f", filepath]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def copy_kube_certs(api: ProxmoxAPI,
                        node: str,
                        src_id,
                        dest_id,
                        cert_paths=config.KUBERNETES_CERT_PATHS):
        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        for cert_path in cert_paths:
            r = PveApi.read_file(api, node, src_id, cert_path)
            content = r["content"]
            # TODO: check truncated content https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
            r = PveApi.write_file(api, node, dest_id, cert_path, content)
