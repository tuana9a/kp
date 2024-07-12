import ipaddress

from proxmoxer import ProxmoxAPI
from kp.service.vm import VmService
from kp.error import *
from kp import util
from kp import config
from kp.payload import *
from typing import List


class PveService:
    @staticmethod
    def clone(api: ProxmoxAPI, node: str, old_id, new_id):
        r = api.nodes(node).qemu(old_id).clone.post(newid=new_id)
        util.log.info(node, "clone", old_id, new_id)
        return r

    # TODO: cache
    @staticmethod
    def list_vm(
            api: ProxmoxAPI,
            node: str,
            id_range=config.PROXMOX_VM_ID_RANGE):
        r = api.nodes(node).qemu.get()
        vm_list: List[VmResponse] = []
        for x in r:
            vm = VmResponse(**x)
            vmid = vm.vmid
            if vmid >= id_range[0] and vmid <= id_range[1]:
                vm_list.append(vm)
        util.log.debug(node, "list_vm", len(vm_list), vm_list)
        return vm_list

    @staticmethod
    def describe_network(api: ProxmoxAPI, node: str, network: str):
        r = api.nodes(node).network(network).get()
        util.log.debug(node, "describe_network", r)
        return r

    @staticmethod
    def new_vm_id(
            api: ProxmoxAPI,
            node: str,
            id_range=config.PROXMOX_VM_ID_RANGE,
            preserved_ids=[]):
        vm_list = PveService.list_vm(api, node, id_range=id_range)
        exist_ids = set()
        exist_ids.update(preserved_ids)
        for vm in vm_list:
            vmid = vm.vmid
            exist_ids.add(vmid)
        util.log.debug("exist_ids", exist_ids)
        new_id = util.find_missing_number(id_range[0], id_range[1], exist_ids)
        if not new_id:
            util.log.error("Can't find new vmid")
            raise GetNewVmIdFailed()
        return new_id

    @staticmethod
    def new_vm_ip(
            api: ProxmoxAPI,
            node: str,
            network_name: str,
            id_range=config.PROXMOX_VM_ID_RANGE,
            preserved_ips=[]):
        r = PveService.describe_network(api, node, network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for vmip in vm_network.hosts():
            ip_pool.append(str(vmip))
        preserved_ips.append(network_gw_ip)
        util.log.debug(node, network_name, "preserved_ips", preserved_ips)
        vm_list = PveService.list_vm(api, node, id_range=id_range)
        exist_ips = set()
        exist_ips.update(preserved_ips)
        for vm in vm_list:
            vmid = vm.vmid
            ifconfig0 = VmService.current_config(api, node,
                                                 vmid).ifconfig(0)
            if not ifconfig0:
                continue
            ip = util.Proxmox.extract_ip(ifconfig0)
            if ip:
                exist_ips.add(ip)
        util.log.debug("exist_ips", exist_ips)
        new_ip = util.find_missing(ip_pool, exist_ips)
        if not new_ip:
            util.log.error("Can't find new ip")
            raise GetNewVmIpFailed()
        return new_ip

    @staticmethod
    def detect_control_planes(
            api: ProxmoxAPI,
            node: str,
            id_range=config.PROXMOX_VM_ID_RANGE,
            **kwargs):
        """
        automatically scan the control planes by tag
        """
        ctlpl_list: List[VmResponse] = util.Proxmox.filter_vm_tag(
            PveService.list_vm(api, node, id_range=id_range),
            config.Tag.ctlpl)
        util.log.info("detect_control_planes", len(ctlpl_list))
        return ctlpl_list

    @staticmethod
    def detect_load_balancers(
            api: ProxmoxAPI,
            node: str,
            id_range=config.PROXMOX_VM_ID_RANGE,
            **kwargs):
        """
        automatically scan the control planes by tag
        """
        lb_list: List[VmResponse] = util.Proxmox.filter_vm_tag(
            PveService.list_vm(api, node, id_range=id_range),
            config.Tag.lb)
        util.log.info("detect_load_balancers", len(lb_list))
        return lb_list
