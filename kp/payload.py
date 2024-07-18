from typing import List, Union
from kp import config


class Cfg:
    def __init__(
            self,
            proxmox_node: str,
            proxmox_host: str,
            proxmox_verify_ssl=False,
            proxmox_user: str = None,
            proxmox_password: str = None,
            proxmox_token_name: str = None,
            proxmox_token_value: str = None,
            vm_id_range: List[int] = config.PROXMOX_VM_ID_RANGE,
            vm_preserved_ids: List[int] = [],
            vm_preserved_ips: List[str] = [],
            vm_ssh_keys: str = "",
            vm_name_prefix="i-",
            **kwargs) -> None:
        self.proxmox_node = proxmox_node
        self.proxmox_host = proxmox_host
        self.proxmox_verify_ssl = proxmox_verify_ssl
        self.proxmox_user = proxmox_user
        self.proxmox_password = proxmox_password
        self.proxmox_token_name = proxmox_token_name
        self.proxmox_token_value = proxmox_token_value
        self.vm_id_range = vm_id_range
        self.vm_preserved_ids = vm_preserved_ids
        self.vm_preserved_ips = vm_preserved_ips
        self.vm_ssh_keys = vm_ssh_keys
        self.vm_name_prefix = vm_name_prefix
        self.kwargs = kwargs
        pass


class VmResponse:
    def __init__(
            self,
            vmid: int,
            status: str,
            name: str = None,
            **kwargs) -> None:
        self.vmid = int(vmid)
        self.name = name
        self.status = status
        self.kwargs = kwargs
        pass

    @property
    def tags(self):
        return self.kwargs.get("tags", "")


class VmConfigResponse:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        pass

    def ifconfig(self, no: int):
        return self.kwargs.get("ipconfig" + str(no), None)
