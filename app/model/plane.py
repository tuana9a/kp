from app.model.kube import KubeVm
from proxmoxer import ProxmoxAPI
from app import config
from app import util


class ControlPlaneVm(KubeVm):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str) -> None:
        super().__init__(api, node, vm_id)

    def drain_node(self,
                   node_name: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION,
                   opts=["--ignore-daemonsets", "--delete-emptydir-data"]):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "drain",
            node_name, *opts
        ]
        # 30 mins should be enough
        return self.exec(cmd, interval_check=5, timeout=30 * 60)

    def delete_node(self,
                    node_name,
                    kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = [
            "kubectl", f"--kubeconfig={kubeconfig_filepath}", "delete", "node",
            node_name
        ]
        return self.exec(cmd, interval_check=5)

    def ensure_cert_dirs(self, dirs=["/etc/kubernetes/pki/etcd"]):
        for d in dirs:
            self.exec(["mkdir", "-p", d], interval_check=3)

    def cat_kubeconfig(self, filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = ["cat", filepath]
        return self.exec(cmd)

    def apply_file(self,
                   filepath: str,
                   kubeconfig_filepath=config.KUBERNETES_ADMIN_CONF_LOCATION):
        cmd = [
            "kubectl", "apply", f"--kubeconfig={kubeconfig_filepath}", "-f",
            filepath
        ]
        return self.exec(cmd)
