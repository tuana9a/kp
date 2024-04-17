from proxmoxer import ProxmoxAPI
from app.model.vm import Vm
from app.error import *
from app import util
from app import config
from app.payload import *
from typing import List


class PveNode:

    def __init__(self, api: ProxmoxAPI, node: str) -> None:
        self.api = api
        self.node = node
        pass

    def clone(self, old_id, new_id):
        api = self.api
        node = self.node

        r = api.nodes(node).qemu(old_id).clone.post(newid=new_id)
        util.log.info(node, "clone", old_id, new_id)
        return r

    def list_vm(self, id_range=config.PROXMOX_VM_ID_RANGE):
        api = self.api
        node = self.node

        r = api.nodes(node).qemu.get()
        vm_list: List[VmResponse] = []
        for x in r:
            vm = VmResponse(**x)
            vmid = vm.vmid
            if vmid >= id_range[0] and vmid <= id_range[1]:
                vm_list.append(vm)
        util.log.debug(node, "list_vm", len(vm_list), vm_list)
        return vm_list

    def describe_network(self, network: str):
        api = self.api
        node = self.node

        r = api.nodes(node).network(network).get()
        util.log.debug(node, "describe_network", r)
        return r

    def new_vm_id(self,
                  vm_list: List[VmResponse] = [],
                  id_range=config.PROXMOX_VM_ID_RANGE,
                  preserved_ids=[]):
        exist_ids = set()
        exist_ids.update(preserved_ids)
        for vm in vm_list:
            id = vm.vmid
            exist_ids.add(id)
        util.log.debug("exist_ids", exist_ids)
        new_id = util.find_missing_number(id_range[0], id_range[1], exist_ids)
        if not new_id:
            util.log.error("Can't find new vm id")
            raise GetNewVmIdFailed()
        return new_id

    def new_vm_ip(
            self,
            vm_list: List[VmResponse] = [],
            ip_pool=[],
            preserved_ips=[]):
        exist_ips = set()
        exist_ips.update(preserved_ips)
        for vm in vm_list:
            id = vm.vmid
            ifconfig0 = Vm(self.api, self.node,
                           id).current_config().ifconfig(0)
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

    def detect_control_planes(self,
                              vm_id_range=config.PROXMOX_VM_ID_RANGE,
                              **kwargs):
        """
        automatically scan the control planes by tag
        """
        ctlpl_list: List[VmResponse] = util.Proxmox.filter_vm_tag(
            self.list_vm(vm_id_range),
            config.Tag.ctlpl)
        util.log.info("detect_control_planes", len(ctlpl_list))
        return ctlpl_list

    def detect_load_balancers(self,
                              vm_id_range=config.PROXMOX_VM_ID_RANGE,
                              **kwargs):
        """
        automatically scan the control planes by tag
        """
        lb_list: List[VmResponse] = util.Proxmox.filter_vm_tag(
            self.list_vm(vm_id_range),
            config.Tag.lb)
        util.log.info("detect_load_balancers", len(lb_list))
        return lb_list
