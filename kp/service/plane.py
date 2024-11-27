import os

from proxmoxer import ProxmoxAPI

from kp import config, error
from kp.client.pve import PveApi


class ControlPlaneService:
    @staticmethod
    def init(api: ProxmoxAPI,
             node: str,
             vm_id: str,
             control_plane_endpoint,
             pod_cidr,
             svc_cidr,
             timeout=10 * 60,
             extra_opts=None):
        if not extra_opts:
            extra_opts = []
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
                            cmd=None,
                            is_control_plane=False,
                            timeout=config.TIMEOUT_IN_SECONDS):
        if not cmd:
            cmd = ["kubeadm", "token", "create", "--print-join-command"]
        exitcode, stdout, stderr = PveApi.exec(api, node, vm_id, cmd, timeout=timeout)
        if exitcode != 0:
            raise error.CreateJoinCmdException(stderr)
        join_cmd = stdout.split()
        if is_control_plane:
            join_cmd.append("--control-plane")
        return join_cmd

    @staticmethod
    def drain_node(api: ProxmoxAPI,
                   node: str,
                   vm_id: str,
                   node_name: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_PATH,
                   opts=None):
        if not opts:
            opts = ["--ignore-daemonsets",
                    "--delete-emptydir-data",
                    "--disable-eviction=true"]
        cmd = ["kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain", node_name]
        cmd.extend(opts)
        # 30 mins should be enough
        exitcode, stdout, stderr = PveApi.exec(api, node, vm_id, cmd, timeout=30 * 60)
        if exitcode != 0:
            raise error.SafeException(f"{node} {vm_id} drain {node_name} failed")
        return exitcode, stdout, stderr

    @staticmethod
    def uncordon_node(api: ProxmoxAPI,
                      node: str,
                      vm_id: str,
                      node_name: str,
                      kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_PATH,
                      opts=None):
        if not opts:
            opts = []
        cmd = ["kubectl", f"--kubeconfig={kubeconfig_filepath}", "uncordon", node_name]
        cmd.extend(opts)
        return PveApi.exec(api, node, vm_id, cmd, timeout=5 * 60)

    @staticmethod
    def delete_node(api: ProxmoxAPI,
                    node: str,
                    vm_id: str,
                    node_name,
                    kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_PATH):
        cmd = ["kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete", "node", node_name]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def ensure_cert_dirs(api: ProxmoxAPI,
                         node: str,
                         vm_id: str,
                         cert_dirs=None):
        if not cert_dirs:
            cert_dirs = [
                "/etc/kubernetes/pki",
                "/etc/kubernetes/pki/etcd",
            ]
        for d in cert_dirs:
            cmd = ["mkdir", "-p", d]
            PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def cat_kubeconfig(api: ProxmoxAPI,
                       node: str,
                       vm_id: str,
                       filepath=config.KUBERNETES_ADMIN_CONF_PATH):
        cmd = ["cat", filepath]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def apply_file(api: ProxmoxAPI,
                   node: str,
                   vm_id: str,
                   filepath: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_PATH):
        cmd = ["kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}", "-f", filepath]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def copy_kube_certs(api: ProxmoxAPI,
                        node: str,
                        src_id,
                        dest_id,
                        cert_paths=None):
        if not cert_paths:
            cert_paths = config.KUBERNETES_CERT_PATHS
        # https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/high-availability/#manual-certs
        for cert_path in cert_paths:
            r = PveApi.read_file(api, node, src_id, cert_path)
            content = r["content"]
            # TODO: check truncated content https://pve.proxmox.com/pve-docs/api-viewer/index.html#/nodes/{node}/qemu/{vmid}/agent/file-read
            r = PveApi.write_file(api, node, dest_id, cert_path, content)

    @staticmethod
    def install_static_pod(api: ProxmoxAPI,
                           node: str,
                           vmid,
                           filename: str,
                           content: str,
                           static_pod_dir=config.KUBERNETES_STATIC_POD_DIR):
        PveApi.write_file(api, node, vmid, os.path.join(static_pod_dir, filename), content)

    @staticmethod
    def uninstall_static_pod(api: ProxmoxAPI,
                             node: str,
                             vmid,
                             filename: str,
                             static_pod_dir=config.KUBERNETES_STATIC_POD_DIR):
        PveApi.exec(api, node, vmid, ["rm", os.path.join(static_pod_dir, filename)])
