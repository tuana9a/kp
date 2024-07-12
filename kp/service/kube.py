from typing import List
from kp.service.vm import VmService
from proxmoxer import ProxmoxAPI
from kp import config
from kp.error import *


class KubeadmService():
    @staticmethod
    def reset(api: ProxmoxAPI,
              node: str,
              vm_id: str, cmd=["kubeadm", "reset", "-f"]):
        return VmService.exec(api, node, vm_id, cmd)

    @staticmethod
    def init(api: ProxmoxAPI,
             node: str,
             vm_id: str,
             control_plane_endpoint,
             pod_cidr,
             svc_cidr=None,
             timeout=10 * 60):
        cmd = [
            "kubeadm",
            "init",
            f"--control-plane-endpoint={control_plane_endpoint}",
            f"--pod-network-cidr={pod_cidr}",
        ]
        if svc_cidr:
            cmd.append(f"--service-cidr={svc_cidr}")
        return VmService.exec(api, node, vm_id, cmd, timeout=timeout)

    @staticmethod
    def create_join_command(api: ProxmoxAPI,
                            node: str,
                            vm_id: str,
                            cmd=["kubeadm", "token", "create",
                                 "--print-join-command"],
                            is_control_plane=False,
                            timeout=config.TIMEOUT_IN_SECONDS,
                            interval_check=3):
        exitcode, stdout, stderr = VmService.exec(
            api, node, vm_id, cmd, timeout=timeout, interval_check=interval_check)
        if exitcode != 0:
            raise CreateJoinCmdFailed(stderr)
        join_cmd: List[str] = stdout.split()
        if is_control_plane:
            join_cmd.append("--control-plane")
        return join_cmd


class KubeVmService():
    @staticmethod
    def restart_containerd(api: ProxmoxAPI,
                           node: str,
                           vm_id: str):
        cmd = ["systemctl", "restart", "containerd"]
        return VmService.exec(
            api, node, vm_id, cmd)

    @staticmethod
    def restart_kubelet(api: ProxmoxAPI,
                        node: str,
                        vm_id: str):
        cmd = ["systemctl", "restart", "kubelet"]
        return VmService.exec(api, node, vm_id, cmd)
