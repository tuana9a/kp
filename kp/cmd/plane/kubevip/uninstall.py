import argparse

from kp import config
from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    plane_ids = args.plane_ids
    for vmid in plane_ids:
        ControlPlaneService.uninstall_static_pod(api, node, vmid, config.KUBEVIP_MANIFEST_FILENAME)


def UninstallCmd(parser: argparse.ArgumentParser):
    parser.add_argument("plane_ids", nargs="+")
    parser.set_defaults(func=run)
