from typing import List, Union
from app import config


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
            vm_template_id: int = None,
            vm_network_name: str = None,
            vm_core_count: int = 8,
            vm_memory: int = 16384,
            vm_disk_size: str = "20G",
            vm_ssh_keys: str = "",
            vm_name_prefix="i-",
            vm_username="u",
            vm_password="1",
            vm_start_on_boot=1,
            install_kube_filepath: str = "./examples/install-kube-1.27.sh",
            install_containerd_filepath: str = "./examples/install-containerd.sh",
            install_kubectl_filepath: str = None,
            containerd_config_filepath: str = "./examples/containerd/config.toml",
            haproxy_cfg: str = "./examples/haproxy.cfg",
            cni_manifest_file: str = "./examples/kube-flannel.yaml",
            pod_cidr="10.244.0.0/16",
            svc_cidr="10.233.0.0/16",
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
        self.vm_template_id = vm_template_id
        self.vm_network_name = vm_network_name
        self.vm_core_count = vm_core_count
        self.vm_memory = vm_memory
        self.vm_disk_size = vm_disk_size
        self.vm_ssh_keys = vm_ssh_keys
        self.vm_name_prefix = vm_name_prefix
        self.vm_username = vm_username
        self.vm_password = vm_password
        self.vm_start_on_boot = vm_start_on_boot
        self.install_kube_filepath = install_kube_filepath
        self.install_containerd_filepath = install_containerd_filepath
        self.install_kubectl_filepath = install_kubectl_filepath
        self.containerd_config_filepath = containerd_config_filepath
        self.haproxy_cfg = haproxy_cfg
        self.cni_manifest_file = cni_manifest_file
        self.pod_cidr = pod_cidr
        self.svc_cidr = svc_cidr
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
