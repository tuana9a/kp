from proxmoxer import ProxmoxAPI

from kp import config
from kp.client.pve import PveApi
from kp.error import *


class VmService:
    @staticmethod
    def systemctl_daemon_reload(api: ProxmoxAPI,
                                node: str,
                                vm_id: str):
        cmd = "systemctl daemon-reload".split()
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def update_containerd_config(api: ProxmoxAPI,
                                 node: str,
                                 vm_id: str,
                                 content=config.CONTAINERD_CONFIG):
        cmd = "mkdir -p /etc/containerd".split()
        PveApi.exec(api, node, vm_id, cmd)
        PveApi.write_file(api, node, vm_id, "/etc/containerd/config.toml", content)

    @staticmethod
    def restart_containerd(api: ProxmoxAPI,
                           node: str,
                           vm_id: str):
        cmd = ["systemctl", "restart", "containerd"]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def restart_kubelet(api: ProxmoxAPI,
                        node: str,
                        vm_id: str):
        cmd = ["systemctl", "restart", "kubelet"]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def kubeadm_reset(api: ProxmoxAPI,
                      node: str,
                      vm_id: str, cmd=["kubeadm", "reset", "-f"]):
        return PveApi.exec(api, node, vm_id, cmd)
