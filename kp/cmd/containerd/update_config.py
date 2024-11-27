import argparse

from kp import config
from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    VmService.update_containerd_config(api, node, vmid, config.CONTAINERD_CONFIG)
    VmService.restart_containerd(api, node, vmid)


def UpdateConfigCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.set_defaults(func=run)
