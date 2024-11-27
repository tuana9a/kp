import argparse

import urllib3

from kp import config
from kp.client.pve import PveApi
from kp.service.lb import LbService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def ScpConfigCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("path", type=str)
    parser.set_defaults(func=run)


def run(args):
    path = args.path
    vm_id = args.vmid
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    with open(path, "r", encoding="utf-8") as f:
        location = config.HAPROXY_CFG_PATH
        PveApi.write_file(api,
                          node,
                          vm_id,
                          location,
                          f.read())
        LbService.reload_haproxy(api, node, vm_id)
