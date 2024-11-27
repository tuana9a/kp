import argparse

import urllib3

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    ids = args.ids
    log.info("vm_ids", ids)
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    for vmid in ids:
        PveApi.startup(api, node, vmid)


def StartCmd(parser: argparse.ArgumentParser):

    parser.add_argument("ids", nargs="+")
    parser.set_defaults(func=run)
