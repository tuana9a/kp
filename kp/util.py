from __future__ import annotations

import argparse
import os
import json
import urllib
import random
import string

from typing import List, Mapping
from proxmoxer import ProxmoxAPI
from kp.logger import Logger
from kp.error import *
from kp import config


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
        manifest = config.KUBEVIP_MANIFEST_TEMPLATE.replace("$INTERFACE", inf).replace("$VIP", vip)
        return manifest


class Cmd:

    def __init__(
        self,
        name: str,
        childs: List[Cmd] = [],
        aliases: List[str] = [],
        parent: Cmd = None,
        sub_level=0,
    ) -> None:
        self.name = name
        self.aliases = aliases
        self.has_child = len(childs) > 0
        self.parent = parent
        self.childs = childs
        self.child_map: Mapping[str, Cmd] = {}
        self.parser = argparse.ArgumentParser()
        self.sub_level = sub_level
        self.setup()
        for child in childs:
            self.add_child(child.name, child)
            for child_alias in child.aliases:
                self.add_child(child_alias, child)
        if self.has_child:
            self.parser.add_argument("subcommand", type=str, choices=self.child_map.keys())
            self.parser.add_argument("remains", type=str, nargs=argparse.REMAINDER)
            self.correct_child_info()

    def add_child(self, name, child: Cmd):
        if self.child_map.get(name, False):
            raise KeyError(f"parent '{self.name}' already has child '{name}'")
        self.child_map[name] = child

    def correct_child_info(self):
        for child in self.childs:
            child.parent = self
            child.sub_level = self.sub_level + 1
            child.parser.prog = " ".join([self.parser.prog, child.name])
            child.correct_child_info()

    def setup(self):
        """
        implement this
        """
        pass

    def call(self, args: List[str]):
        self.args = args
        self.parsed_args = self.parser.parse_args(args)
        self.run()
        if self.has_child:
            self.run_child()

    def run_child(self):
        child = self.child_map.get(self.parsed_args.subcommand, None)
        if not child:
            raise KeyError(self.parsed_args.subcommand)
        child.call(self.parsed_args.remains)
        pass

    def run(self):
        """
        implement this
        """
        pass

    def tree(self, current_level=0, recursive=True):
        name = self.name
        if len(self.aliases):
            name += f" ({','.join(self.aliases)})"
        print(
            current_level * "    ",
            name,
        )
        if recursive:
            for child in self.childs:
                child.tree(current_level + 1)
