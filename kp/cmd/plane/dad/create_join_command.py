import argparse

from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    log.info("vmid", vmid, "create-join-token")
    ControlPlaneService.create_join_command(api, node, vmid)


def CreateJoinCommandCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.set_defaults(func=run)
