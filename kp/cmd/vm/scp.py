import argparse

import urllib3

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    localpath = args.localpath
    path = args.path
    vm_id = args.vmid
    urllib3.disable_warnings()
    log.info("vm_id", vm_id)
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    log.info(localpath, "->", path)
    with open(localpath, "r", encoding="utf-8") as f:
        PveApi.write_file(api, node, vm_id, path, f.read())


def ScpCmd(parser: argparse.ArgumentParser):

    parser.add_argument("vmid", type=int)
    parser.add_argument("localpath", type=str)
    parser.add_argument("path", type=str)
    parser.set_defaults(func=run)
