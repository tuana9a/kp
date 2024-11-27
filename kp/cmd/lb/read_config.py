import argparse

import urllib3

from kp.service.lb import LbService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vm_id = args.lbid
    print(LbService.read_haproxy_config(api, node, vm_id)["content"])


def ReadConfigCmd(parser: argparse.ArgumentParser):
    parser.add_argument("lbid", type=int)
    parser.set_defaults(func=run)
