import argparse

from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    VmService.restart_kubelet(api, node, vmid)


def RestartCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.set_defaults(func=run)