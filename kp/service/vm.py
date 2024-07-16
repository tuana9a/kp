import time

from typing import List
from proxmoxer import ProxmoxAPI
from kp.error import *
from kp import config
from kp import util
from kp.payload import VmConfigResponse


class VmService:
    @staticmethod
    def systemctl_daemon_reload(api: ProxmoxAPI,
                                node: str,
                                vm_id: str):
        cmd = "systemctl daemon-reload".split()
        return PveService.exec(api, node, vm_id, cmd)

    @staticmethod
    def update_containerd_config(api: ProxmoxAPI,
                                 node: str,
                                 vm_id: str,
                                 filepath: str):
        cmd = "mkdir -p /etc/containerd".split()
        PveService.exec(api, node, vm_id, cmd, interval_check=2)
        with open(filepath) as f:
            path = "/etc/containerd/config.toml"
            PveService.write_file(api, node, vm_id, path, f.read())

    @staticmethod
    def restart_containerd(api: ProxmoxAPI,
                           node: str,
                           vm_id: str):
        cmd = ["systemctl", "restart", "containerd"]
        return PveService.exec(api, node, vm_id, cmd)

    @staticmethod
    def restart_kubelet(api: ProxmoxAPI,
                        node: str,
                        vm_id: str):
        cmd = ["systemctl", "restart", "kubelet"]
        return PveService.exec(api, node, vm_id, cmd)

    @staticmethod
    def kubeadm_reset(api: ProxmoxAPI,
                      node: str,
                      vm_id: str, cmd=["kubeadm", "reset", "-f"]):
        return PveService.exec(api, node, vm_id, cmd)
