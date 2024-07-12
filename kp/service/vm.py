import time

from typing import List
from proxmoxer import ProxmoxAPI
from kp.error import *
from kp import config
from kp import util
from kp.payload import VmConfigResponse


class VmService:
    @staticmethod
    def exec(api: ProxmoxAPI,
             node: str,
             vm_id: str,
             cmd: List[str],
             timeout=config.TIMEOUT_IN_SECONDS,
             interval_check=10):
        duration = 0
        r = api.nodes(node).qemu(vm_id).agent.exec.post(command=cmd)
        pid = r["pid"]
        util.log.info(node, vm_id, "exec", pid, cmd)
        exited = 0
        stdout: str = None
        stderr: str = None
        exitcode: int = None
        while True:
            util.log.info(node, vm_id, "exec", pid, "WAIT", duration)
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                util.log.error(node, vm_id, "exec", pid, "TIMEOUT")
                raise TimeoutError()
            status = api.nodes(node).qemu(vm_id).agent("exec-status").get(
                pid=pid)
            exited = status["exited"]
            stdout = status.get("out-data", None)
            stderr = status.get("err-data", None)
            exitcode = status.get("exitcode", None)
            if exited:
                break
        util.log.info(
            node,
            vm_id,
            "exec",
            pid,
            "duration",
            duration,
            "exitcode",
            exitcode)
        if stdout:
            util.log.debug(node, vm_id, "exec", pid, "stdout\n" + str(stdout))
        if stderr:
            util.log.debug(node, vm_id, "exec", pid, "stderr\n" + str(stderr))
        if exitcode:
            util.log.error(node, vm_id, "exec", pid, "stderr\n" + str(stderr))
        return exitcode, stdout, stderr

    @staticmethod
    def wait_for_guest_agent(api: ProxmoxAPI,
                             node: str,
                             vm_id: str,
                             timeout=config.TIMEOUT_IN_SECONDS,
                             interval_check=15):

        duration = 0
        while True:
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                util.log.error(node, vm_id, "wait_for_guest_agent", "TIMEOUT")
                raise TimeoutError()
            try:
                api.nodes(node).qemu(vm_id).agent.ping.post()
                break
            except Exception as err:
                util.log.info(node, vm_id, "wait_for_guest_agent",
                              "WAIT", duration)
        util.log.info(node, vm_id, "wait_for_guest_agent", "DONE")

    @staticmethod
    def wait_for_cloud_init(api: ProxmoxAPI,
                            node: str,
                            vm_id: str,
                            timeout=config.TIMEOUT_IN_SECONDS,
                            interval_check=15):
        return VmService.exec(api, node, vm_id, "cloud-init status --wait",
                              timeout=timeout,
                              interval_check=interval_check)

    @staticmethod
    def wait_for_shutdown(api: ProxmoxAPI,
                          node: str,
                          vm_id: str,
                          timeout=config.TIMEOUT_IN_SECONDS,
                          interval_check=15):

        status = None
        duration = 0
        while True:
            util.log.info(node, vm_id, "wait_for_shutdown", "WAIT", duration)
            time.sleep(interval_check)
            duration += interval_check
            if duration > timeout:
                util.log.error(node, vm_id, "wait_for_shutdown", "TIMEOUT")
                raise TimeoutError()
            try:
                r = api.nodes(node).qemu(vm_id).status.current.get()
                status = r["status"]
                if status == "stopped":
                    break
            except Exception as err:
                util.log.error("shutdown", err)

    @staticmethod
    def update_config(api: ProxmoxAPI,
                      node: str,
                      vm_id: str, **kwargs):  # TODO: rename kwargs to update_body

        util.log.info(node, vm_id, "update_config")
        util.log.debug(node, vm_id, "update_config", kwargs)
        r = api.nodes(node).qemu(vm_id).config.put(**kwargs)
        util.log.debug(node, vm_id, "update_config", r)
        return r

    @staticmethod
    def current_config(api: ProxmoxAPI,
                       node: str,
                       vm_id: str):

        r = api.nodes(node).qemu(vm_id).config.get()
        vm_config = VmConfigResponse(**r)
        util.log.debug(node, vm_id, "current_config", vm_config)
        return vm_config

    @staticmethod
    def current_status(api: ProxmoxAPI,
                       node: str,
                       vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.current.get()
        util.log.debug(node, vm_id, "current_status", r)
        return r

    @staticmethod
    def resize_disk(api: ProxmoxAPI,
                    node: str,
                    vm_id: str, disk: str, size: str):

        util.log.info(node, vm_id, "resize_disk", disk, size)
        r = api.nodes(node).qemu(vm_id).resize.put(disk=disk, size=size)
        util.log.debug(node, vm_id, "resize_disk", r)
        return r

    @staticmethod
    def startup(api: ProxmoxAPI,
                node: str,
                vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.start.post()
        util.log.debug(node, vm_id, "startup", r)
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
        util.log.debug(node, vm_id, "shutdown", r)
        return r

    @staticmethod
    def reboot(api: ProxmoxAPI,
               node: str,
               vm_id: str):

        r = api.nodes(node).qemu(vm_id).status.reboot.post()
        util.log.debug(node, vm_id, "reboot", r)
        return r

    @staticmethod
    def write_file(api: ProxmoxAPI,
                   node: str,
                   vm_id: str, filepath: str, content: str):

        r = api.nodes(node).qemu(vm_id).agent("file-write").post(
            content=content, file=filepath)
        util.log.debug(node, vm_id, "write_file", filepath, "\n" + content)
        return r

    @staticmethod
    def delete(api: ProxmoxAPI,
               node: str,
               vm_id: str):

        r = api.nodes(node).qemu(vm_id).delete()
        util.log.debug(node, vm_id, "delete", r)

        # FIXME: implement wait for deletion
        time.sleep(5)
        return r

    @staticmethod
    def read_file(api: ProxmoxAPI,
                  node: str,
                  vm_id: str, filepath: str):

        r = api.nodes(node).qemu(vm_id).agent("file-read").get(file=filepath)
        util.log.debug(node, vm_id, "read_file", r)
        return r
