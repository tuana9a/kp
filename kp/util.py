import os
import json
import urllib
import random
import string

from proxmoxer import ProxmoxAPI
from kp.logger import Logger
from kp.error import *
from kp import config
from kp import template


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
        return config.Cfg(**json.loads(f.read()))


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
    def create_api_client(cfg: config.Cfg):
        # TODO: verify with ca cert
        if cfg.proxmox_token_name:
            log.info("auth using proxmox_token")
            return ProxmoxAPI(cfg.proxmox_host,
                              port=cfg.proxmox_port,
                              user=cfg.proxmox_user,
                              token_name=cfg.proxmox_token_name,
                              token_value=cfg.proxmox_token_value,
                              verify_ssl=cfg.proxmox_verify_ssl)
        log.info("auth using proxmox_password")
        return ProxmoxAPI(
            cfg.proxmox_host,
            user=cfg.proxmox_user,
            password=cfg.proxmox_password,
            verify_ssl=False,
        )


class Kubevip():
    @staticmethod
    def render_pod_manifest(inf: str, vip: str):
        manifest = template.KUBEVIP_MANIFEST_TEMPLATE.replace("$INTERFACE", inf).replace("$VIP", vip)
        return manifest
