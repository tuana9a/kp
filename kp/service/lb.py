import os
import ipaddress
from typing import List

from proxmoxer import ProxmoxAPI
from kp.client.pve import PveApi
from kp import util
from kp import config
from kp import template
from kp.service.vm import VmService
from kp.payload import VmResponse


class LbService:
    @staticmethod
    def install_haproxy(api: ProxmoxAPI,
                        node: str,
                        vm_id: str):
        cmd = ["apt", "install", "-y", "haproxy"]
        return PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def read_haproxy_config(api: ProxmoxAPI,
                            node: str,
                            vm_id: str,
                            config_path=config.HAPROXY_CFG_PATH):
        return PveApi.read_file(api, node, vm_id, config_path)

    @staticmethod
    def update_haproxy_config(api: ProxmoxAPI,
                              node: str,
                              vm_id: str,
                              config_content: str,
                              config_path=config.HAPROXY_CFG_PATH):
        PveApi.write_file(api, node, vm_id, config_path, config_content)

    @staticmethod
    def reload_haproxy(api: ProxmoxAPI,
                       node: str,
                       vm_id: str):
        cmd = ["systemctl", "reload", "haproxy"]
        PveApi.exec(api, node, vm_id, cmd)

    @staticmethod
    def render_haproxy_config(backends: list):
        tmpl = template.HAPROXY_CONFIG_TEMPLATE
        backends_content = ""
        indent = 4 * " "
        for backend in backends:
            vm_id = backend[0]
            vm_ip = backend[1]
            backends_content += indent + f"server {vm_id} {vm_ip}:6443 check\n"
        config_content = tmpl.format(control_plane_backends=backends_content)
        return config_content
