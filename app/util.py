import os
import json
import urllib
import random
import string

from app.logger import Logger
from app.error import *
from proxmoxer import ProxmoxAPI
from app import config

log = Logger.from_env()

# includes uppercase letters, lowercase letters, and digits
characters = string.ascii_lowercase + string.digits


def find_missing_number(start, end, existed: set):
    i = start
    while i <= end:
        if i not in existed:
            return i
        i = i + 1
    return None


def find_missing(arr: list, existed: set):
    i = 0
    end = len(arr)
    while i < end:
        value = arr[i]
        if value not in existed:
            return value
        i = i + 1
    return None


def gen_characters(length: int):
    random_string = ''.join(random.choice(characters) for _ in range(length))
    return random_string


def load_config(config_path=os.getenv("KP_CONFIG")):
    log.info("config_path", config_path)
    if not config_path:
        raise ValueError("KP_CONFIG is not set")
    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)
    with open(config_path, "r") as f:
        return json.loads(f.read())


class Proxmox:

    @staticmethod
    def extract_ip(ifconfig_n: str):
        """
        Example: "ip=192.168.56.123/24,gw=192.168.56.1"
        """
        parts = ifconfig_n.split(",")
        parts = parts[0].split("=")
        parts = parts[1].split("/")
        ip = parts[0]
        return ip

    @staticmethod
    def encode_sshkeys(sshkeys: str):
        if not sshkeys:
            return None
        # NOTE: https://github.com/proxmoxer/proxmoxer/issues/153
        return urllib.parse.quote(sshkeys, safe="")

    @staticmethod
    def create_api_client(proxmox_host,
                          proxmox_user,
                          proxmox_password=None,
                          proxmox_token_name=None,
                          proxmox_token_value=None,
                          proxmox_verify_ssl=False,
                          **kwargs):
        # TODO: verify later with ca cert
        if proxmox_token_name:
            log.info("using proxmox_token")
            return ProxmoxAPI(proxmox_host,
                              user=proxmox_user,
                              token_name=proxmox_token_name,
                              token_value=proxmox_token_value,
                              verify_ssl=proxmox_verify_ssl)
        log.info("using proxmox_password")
        return ProxmoxAPI(
            proxmox_host,
            user=proxmox_user,
            password=proxmox_password,
            verify_ssl=False,
        )

    def filter_vm_id(vm_list: list, vm_id: int):

        for x in vm_list:
            id = x["vmid"]
            if str(id) == str(vm_id):
                log.debug("util.filter_id", x)
                return x

        raise VmNotFoundException(vm_id)

    def filter_vm_tag(vm_list: list,
                      tag: str,
                      delimiter=config.PROXMOX_VM_TAG_DELIMITER):

        result = []

        for vm in vm_list:
            id = vm["vmid"]
            tags = set(vm.get("tags", "").split(delimiter))
            if tag in tags:
                result.append(vm)
        log.debug("util.filter_tag", len(result), result)
        return result


class Haproxy:

    @staticmethod
    def render_backends_config(backends: list):
        content = ""
        for backend in backends:
            vm_id = backend["vmid"]
            vm_ip = backend["vmip"]
            # TODO: indent is configurable
            content += 4 * " " + f"server {vm_id} {vm_ip}:6443 check\n"
        return content
