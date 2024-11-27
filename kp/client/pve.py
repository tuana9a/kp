import ipaddress
import time
from typing import List

from proxmoxer import ProxmoxAPI

from kp import config, error, payload, util
from kp.util.log import log


class PveApi:
    @staticmethod
    def clone(api: ProxmoxAPI, node: str, old_id, new_id):
        r = api.nodes(node).qemu(old_id).clone.post(newid=new_id)
        log.info(node, "clone", old_id, new_id)
        return r

    # TODO: cache
    @staticmethod
    def list_vm(api: ProxmoxAPI, node: str):
        r = api.nodes(node).qemu.get()
        vm_list: List[payload.VmResponse] = []
        id_range = config.DEFAULT_PROXMOX_VM_ID_RANGE
        for x in r:
            vm = payload.VmResponse(**x)
            vmid = vm.vmid
            if vmid >= id_range[0] and vmid <= id_range[1]:
                vm_list.append(vm)
        log.debug(node, "list_vm", len(vm_list), vm_list)
        return vm_list

    @staticmethod
    def find_vm_by_id(api: ProxmoxAPI,
                      node: str, vmid) -> payload.VmResponse:
        r = api.nodes(node).qemu.get()
        for x in r:
            vm = payload.VmResponse(**x)
            if str(vm.vmid) == str(vmid):
                return vm
        raise error.VmNotFoundException(vmid)

    @staticmethod
    def describe_network(api: ProxmoxAPI, node: str, network: str):
        r = api.nodes(node).network(network).get()
        log.debug(node, "describe_network", r)
        ip = r["address"]
        netmask = r["netmask"]
        cidr = r["cidr"]
        return {
            "ip": ip,
            "netmask": netmask,
            "cidr": cidr,
        }

    @staticmethod
    def new_vm_id(api: ProxmoxAPI, node: str):
        id_range = config.DEFAULT_PROXMOX_VM_ID_RANGE
        preserved_ids = config.DEFAULT_PROXMOX_PRESERVED_VM_IDS
        vm_list = PveApi.list_vm(api, node)
        exist_ids = set()
        exist_ids.update(preserved_ids)
        for vm in vm_list:
            vmid = vm.vmid
            exist_ids.add(vmid)
        log.debug("exist_ids", exist_ids)
        new_id = util.num.find_missing_number(id_range[0], id_range[1], exist_ids)
        if not new_id:
            log.error("Can't find new vmid")
            raise error.NewVmIdException()
        return new_id

    @staticmethod
    def new_vm_ip(api: ProxmoxAPI,
                  node: str,
                  network_name: str):
        preserved_ips = config.DEFAULT_PROXMOX_PRESERVED_VM_IPS
        network = PveApi.describe_network(api, node, network_name)
        network_interface = ipaddress.IPv4Interface(network["cidr"])
        network_gw_ip = network["ip"]
        vm_network = network_interface.network
        ip_pool = []
        for vmip in vm_network.hosts():
            ip_pool.append(str(vmip))
        preserved_ips.append(network_gw_ip)
        log.debug(node, network_name, "preserved_ips", preserved_ips)
        vm_list = PveApi.list_vm(api, node)
        exist_ips = set()
        exist_ips.update(preserved_ips)
        for vm in vm_list:
            vmid = vm.vmid
            ifconfig0 = PveApi.current_config(api, node,
                                              vmid).ifconfig(0)
            if not ifconfig0:
                continue
            ip = util.proxmox.extract_ip(ifconfig0)
            if ip:
                exist_ips.add(ip)
        log.debug("exist_ips", exist_ips)
        new_ip = util.num.find_missing(ip_pool, exist_ips)
        if not new_ip:
            log.error("Can't find new ip")
            raise error.NewVmIpException()
        return new_ip

    @staticmethod
    # TODO: refactor
    def detect_control_planes(api: ProxmoxAPI,
                              node: str,
                              **kwargs):
        """
        automatically scan the control planes by tag
        """
        tag = config.Tag.ctlpl
        delimiter = config.PROXMOX_VM_TAG_DELIMITER
        result = []
        vm_list = PveApi.list_vm(api, node)
        for x in vm_list:
            tags = set(x.tags.split(delimiter))
            if tag in tags:
                result.append(x)
        log.info("detect_control_planes", len(result))
        return result

    @staticmethod
    # TODO: refactor
    def detect_load_balancers(api: ProxmoxAPI,
                              node: str,
                              **kwargs):
        """
        automatically scan the control planes by tag
        """
        tag = config.Tag.lb
        delimiter = config.PROXMOX_VM_TAG_DELIMITER
        result = []
        vm_list = PveApi.list_vm(api, node)
        for x in vm_list:
            tags = set(x.tags.split(delimiter))
            if tag in tags:
                result.append(x)
        log.info("detect_load_balancers", len(result))
        return result

    @staticmethod
    def delete_vm(api: ProxmoxAPI,
                  node: str,
                  vm_id):
        r = api.nodes(node).qemu(vm_id).delete()
        log.debug(node, vm_id, "delete", r)

        # wait for deletion
        max_count = 10
        count = 0
        while count < max_count:
            try:
                vm = PveApi.find_vm_by_id(api, node, vm_id)
            except error.VmNotFoundException as err:
                log.error(err)
                return r
            count = count + 1
            time.sleep(3)

        log.error("max_count exceeded")
        return r

    @staticmethod
    def exec(api: ProxmoxAPI,
             node: str,
             vm_id: str,
             cmd: List[str],
             timeout=config.TIMEOUT_IN_SECONDS):
        interval_check = 3
        duration = 0
        r = api.nodes(node).qemu(vm_id).agent.exec.post(command=cmd)
        pid = r["pid"]
        log.info(node, vm_id, "exec", pid, cmd)
        exited = 0
        stdout: str = None
        stderr: str = None
        exitcode: int = None

        while True:
            if duration > timeout:
                log.error(node, vm_id, "exec", pid, "TIMEOUT")
                raise TimeoutError()
            try:
                status = api.nodes(node).qemu(vm_id).agent("exec-status").get(pid=pid)
                log.debug(node, vm_id, "exec", pid, "duration", duration, status)
                exited = status["exited"]
                stdout = status.get("out-data", None)
                stderr = status.get("err-data", None)
                exitcode = status.get("exitcode", None)
                if exited:
                    break
            except Exception as err:
                log.error(node, vm_id, "exec", pid, "duration", duration, f"ERROR {err}")
                break
            time.sleep(interval_check)
            duration += interval_check

        log.info(node, vm_id, "exec", pid, "duration", duration, "exitcode", exitcode)
        out = ""
        if stdout:
            out += "=== stdout ===\n" + str(stdout)
        if stderr:
            out += "=== stderr ===\n" + str(stderr)
        log.debug(node, vm_id, "exec", pid, "out\n" + str(out))
        return exitcode, stdout, stderr

    @staticmethod
    def wait_for_guestagent(api: ProxmoxAPI,
                            node: str,
                            vm_id: str,
                            timeout=config.TIMEOUT_IN_SECONDS,
                            interval_check=3):

        duration = 0
        while True:
            if duration > timeout:
                log.error(node, vm_id, PveApi.wait_for_guestagent.__name__, "TIMEOUT")
                raise TimeoutError()
            try:
                api.nodes(node).qemu(vm_id).agent.ping.post()
                break
            except Exception as err:
                log.info(node, vm_id, PveApi.wait_for_guestagent.__name__, "WAIT", duration, err)
                time.sleep(interval_check)
                duration += interval_check
        log.info(node, vm_id, PveApi.wait_for_guestagent.__name__, "DONE")

    @staticmethod
    def wait_for_cloudinit(api: ProxmoxAPI,
                           node: str,
                           vm_id: str,
                           timeout=config.TIMEOUT_IN_SECONDS):
        return PveApi.exec(api, node, vm_id, "cloud-init status --wait", timeout=timeout)

    @staticmethod
    def wait_for_shutdown(api: ProxmoxAPI,
                          node: str,
                          vm_id: str,
                          timeout=config.TIMEOUT_IN_SECONDS,
                          interval_check=3):

        status = None
        duration = 0
        while True:
            if duration > timeout:
                log.error(node, vm_id, PveApi.wait_for_shutdown.__name__, "TIMEOUT")
                raise TimeoutError()
            r = api.nodes(node).qemu(vm_id).status.current.get()
            status = r["status"]
            if status == "stopped":
                break
            log.info(node, vm_id, PveApi.wait_for_shutdown.__name__, "WAIT", duration)
            time.sleep(interval_check)
            duration += interval_check

    @staticmethod
    def update_config(api: ProxmoxAPI,
                      node: str,
                      vm_id: str, **kwargs):  # TODO: rename kwargs to update_body

        log.info(node, vm_id, "update_config")
        log.debug(node, vm_id, "update_config", kwargs)
        r = api.nodes(node).qemu(vm_id).config.put(**kwargs)
        log.debug(node, vm_id, "update_config", r)
        return r

    @staticmethod
    def current_config(api: ProxmoxAPI,
                       node: str,
                       vm_id: str):

        r = api.nodes(node).qemu(vm_id).config.get()
        vm_config = payload.VmConfigResponse(**r)
        log.debug(node, vm_id, "current_config", vm_config)
        return vm_config

    @staticmethod
    def current_status(api: ProxmoxAPI,
                       node: str,
                       vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.current.get()
        log.debug(node, vm_id, "current_status", r)
        return r

    @staticmethod
    def resize_disk(api: ProxmoxAPI,
                    node: str,
                    vm_id: str, disk: str, size: str):

        log.info(node, vm_id, "resize_disk", disk, size)
        r = api.nodes(node).qemu(vm_id).resize.put(disk=disk, size=size)
        log.debug(node, vm_id, "resize_disk", r)
        return r

    @staticmethod
    def startup(api: ProxmoxAPI,
                node: str,
                vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.start.post()
        log.debug(node, vm_id, "startup", r)
        return r

    @staticmethod
    def shutdown(api: ProxmoxAPI,
                 node: str,
                 vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.current.get()
        status = r["status"]
        if status == "stopped":
            return None
        r = api.nodes(node).qemu(vm_id).status.shutdown.post()
        log.debug(node, vm_id, "shutdown", r)
        return r

    @staticmethod
    def reboot(api: ProxmoxAPI,
               node: str,
               vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.reboot.post()
        log.debug(node, vm_id, "reboot", r)
        return r

    @staticmethod
    def write_file(api: ProxmoxAPI,
                   node: str,
                   vm_id: str, filepath: str, content: str):

        r = api.nodes(node).qemu(vm_id).agent("file-write").post(
            content=content, file=filepath)
        log.debug(node, vm_id, "write_file", filepath, "\n" + content)
        return r

    @staticmethod
    def read_file(api: ProxmoxAPI,
                  node: str,
                  vm_id: str, filepath: str):
        log.debug(node, vm_id, "read_file", filepath)
        r = api.nodes(node).qemu(vm_id).agent("file-read").get(file=filepath)
        return r

    @staticmethod
    def copy_file_vm2vm(api: ProxmoxAPI,
                        node: str,
                        src_id,
                        dest_id,
                        filepath: str):
        r = PveApi.read_file(api, node, src_id, filepath)
        r = PveApi.write_file(api, node, dest_id, filepath, r["content"])
