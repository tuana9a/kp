from typing import List
from app.model.vm import Vm
from proxmoxer import ProxmoxAPI
from app import config
from app.error import *


class KubeVm(Vm):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str) -> None:
        super().__init__(api, node, vm_id)

    def kubeadm_reset(self, cmd=["kubeadm", "reset", "-f"]):
        return self.exec(cmd)

    def kubeadm_init(self,
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
        return self.exec(cmd, timeout=timeout)

    def create_join_command(self,
                            cmd=["kubeadm", "token", "create",
                                 "--print-join-command"],
                            is_control_plane=False,
                            timeout=config.TIMEOUT_IN_SECONDS,
                            interval_check=3):
        exitcode, stdout, stderr = self.exec(cmd,
                                             timeout=timeout,
                                             interval_check=interval_check)
        if exitcode != 0:
            raise CreateJoinCmdFailed(stderr)
        join_cmd: List[str] = stdout.split()
        if is_control_plane:
            join_cmd.append("--control-plane")
        return join_cmd

    def restart_containerd(self):
        return self.exec("systemctl restart containerd")

    def restart_kubelet(self):
        return self.exec("systemctl restart kubelet")
