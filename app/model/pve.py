from proxmoxer import ProxmoxAPI
from app.model.vm import Vm
from app.error import *
from app import util
from app import config


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
        vm_list = []
        for vm in r:
            vmid = vm["vmid"]
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
                  vm_list=[],
                  id_range=config.PROXMOX_VM_ID_RANGE,
                  preserved_ids=[]):
        exist_ids = set()
        exist_ids.update(preserved_ids)
        for vm in vm_list:
            id = vm["vmid"]
            exist_ids.add(id)
        util.log.debug("exist_ids", exist_ids)
        new_id = util.find_missing_number(id_range[0], id_range[1], exist_ids)
        if not new_id:
            util.log.error("Can't find new vm id")
            raise GetNewVmIdFailed()
        return new_id

    def new_vm_ip(self, vm_list=[], ip_pool=[], preserved_ips=[]):
        exist_ips = set()
        exist_ips.update(preserved_ips)
        for vm in vm_list:
            id = vm["vmid"]
            config = Vm(self.api, self.node, id).current_config()
            ifconfig0 = config.get("ipconfig0", None)
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

        vm_list = self.list_vm(vm_id_range)
        ctlpl_vm_list = util.Proxmox.filter_vm_tag(vm_list, config.Tag.ctlpl)
        control_planes = []

        if not len(ctlpl_vm_list):
            return control_planes
        util.log.info("ctlpl_vm_list", "DETECTED")

        for vm in ctlpl_vm_list:
            vmid = vm["vmid"]
            vmctl = Vm(self.api, self.node, vmid)
            current_config = vmctl.current_config()
            ifconfig0 = current_config.get("ipconfig0", None)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                control_planes.append({"vmid": vmid, "vmip": vmip})
        return control_planes

    def detect_load_balancers(self,
                              vm_id_range=config.PROXMOX_VM_ID_RANGE,
                              **kwargs):
        """
        automatically scan the control planes by tag
        """

        vm_list = self.list_vm(vm_id_range)
        lb_vm_list = util.Proxmox.filter_vm_tag(vm_list, config.Tag.lb)
        load_balancers = []

        if not len(lb_vm_list):
            return load_balancers
        util.log.info("lb_vm_list", "DETECTED")

        for vm in lb_vm_list:
            vmid = vm["vmid"]
            vmctl = Vm(self.api, self.node, vmid)
            current_config = vmctl.current_config()
            ifconfig0 = current_config.get("ipconfig0", None)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                load_balancers.append({"vmid": vmid, "vmip": vmip})
        return load_balancers
