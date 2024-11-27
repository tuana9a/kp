import argparse

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    vmid = args.vmid
    log.info("vmid", vmid)
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    PveApi.wait_for_guestagent(api, node, vmid)


def WaitCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.set_defaults(func=run)
