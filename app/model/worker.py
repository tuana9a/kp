from app.model.kube import KubeVm
from proxmoxer import ProxmoxAPI


class WorkerVm(KubeVm):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str) -> None:
        super().__init__(api, node, vm_id)
