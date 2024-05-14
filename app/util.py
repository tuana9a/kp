import os
import json
import urllib
import random
import string

from typing import List
from app.logger import Logger
from app.error import *
from proxmoxer import ProxmoxAPI
from app import config
from app.payload import *


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
        return Cfg(**json.loads(f.read()))


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
    def create_api_client(cfg: Cfg):
        # TODO: verify later with ca cert
        if cfg.proxmox_token_name:
            log.info("using proxmox_token")
            return ProxmoxAPI(cfg.proxmox_host,
                              user=cfg.proxmox_user,
                              token_name=cfg.proxmox_token_name,
                              token_value=cfg.proxmox_token_value,
                              verify_ssl=cfg.proxmox_verify_ssl)
        log.info("using proxmox_password")
        return ProxmoxAPI(
            cfg.proxmox_host,
            user=cfg.proxmox_user,
            password=cfg.proxmox_password,
            verify_ssl=False,
        )

    def filter_vm_id(vm_list: List[VmResponse], vm_id: int):
        for x in vm_list:
            if str(x.vmid) == str(vm_id):
                log.debug("util.filter_id", x.vmid)
                return x

        raise VmNotFoundException(vm_id)

    def filter_vm_tag(vm_list: List[VmResponse],
                      tag: str,
                      delimiter=config.PROXMOX_VM_TAG_DELIMITER):

        result: List[VmResponse] = []

        for x in vm_list:
            tags = set(x.tags.split(delimiter))
            if tag in tags:
                result.append(x)
        log.debug("util.filter_tag", tag,
                  list(map(lambda x: x.vmid, result)))
        return result


class Haproxy:

    @staticmethod
    def render_backends_config(backends: list):
        content = ""
        for backend in backends:
            vm_id = backend[0]
            vm_ip = backend[1]
            # TODO: indent is configurable
            content += 4 * " " + f"server {vm_id} {vm_ip}:6443 check\n"
        return content
