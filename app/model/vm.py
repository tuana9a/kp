import time

from typing import List
from proxmoxer import ProxmoxAPI
from app.error import *
from app import config
from app import util
from app.payload import VmConfigResponse


class Vm:

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str) -> None:
        self.api = api
        self.node = node
        self.vm_id = vm_id

    def exec(self,
             cmd: List[str],
             timeout=config.TIMEOUT_IN_SECONDS,
             interval_check=10):
        api = self.api
        node = self.node
        vm_id = self.vm_id
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

    def wait_for_guest_agent(self,
                             timeout=config.TIMEOUT_IN_SECONDS,
                             interval_check=15):
        api = self.api
        node = self.node
        vm_id = self.vm_id

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

    def wait_for_cloud_init(self,
                            timeout=config.TIMEOUT_IN_SECONDS,
                            interval_check=15):
        return self.exec("cloud-init status --wait",
                         timeout=timeout,
                         interval_check=interval_check)

    def wait_for_shutdown(self,
                          timeout=config.TIMEOUT_IN_SECONDS,
                          interval_check=15):
        api = self.api
        node = self.node
        vm_id = self.vm_id

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

    def update_config(self, **kwargs):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        util.log.info(node, vm_id, "update_config")
        util.log.debug(node, vm_id, "update_config", kwargs)
        r = api.nodes(node).qemu(vm_id).config.put(**kwargs)
        util.log.debug(node, vm_id, "update_config", r)
        return r

    def current_config(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).config.get()
        vm_config = VmConfigResponse(**r)
        util.log.debug(node, vm_id, "current_config", vm_config)
        return vm_config

    def current_status(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).status.current.get()
        util.log.debug(node, vm_id, "current_status", r)
        return r

    def resize_disk(self, disk: str, size: str):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        util.log.info(node, vm_id, "resize_disk", disk, size)
        r = api.nodes(node).qemu(vm_id).resize.put(disk=disk, size=size)
        util.log.debug(node, vm_id, "resize_disk", r)
        return r

    def startup(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).status.start.post()
        util.log.debug(node, vm_id, "startup", r)
        return r

    def shutdown(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).status.current.get()
        status = r["status"]
        if status == "stopped":
            return None
        r = api.nodes(node).qemu(vm_id).status.shutdown.post()
        util.log.debug(node, vm_id, "shutdown", r)
        return r

    def reboot(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).status.reboot.post()
        util.log.debug(node, vm_id, "reboot", r)
        return r

    def write_file(self, filepath: str, content: str):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).agent("file-write").post(
            content=content, file=filepath)
        util.log.debug(node, vm_id, "write_file", filepath, "\n" + content)
        return r

    def delete(self):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).delete()
        util.log.debug(node, vm_id, "delete", r)
        return r

    def read_file(self, filepath: str):
        api = self.api
        node = self.node
        vm_id = self.vm_id

        r = api.nodes(node).qemu(vm_id).agent("file-read").get(file=filepath)
        util.log.debug(node, vm_id, "read_file", r)
        return r
