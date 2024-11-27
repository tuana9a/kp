import argparse

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    src_id = args.srcid
    dest_id = args.destid
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    PveApi.clone(api, node, src_id, dest_id)


def CloneCmd(parser: argparse.ArgumentParser):
    parser.add_argument("srcid", type=int)
    parser.add_argument("destid", type=int)
    parser.set_defaults(func=run)
