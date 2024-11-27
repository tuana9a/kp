import argparse

from kp import config, util
from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    plane_ids = args.plane_ids
    vip = args.vip
    inf = args.inf
    manifest = util.kubevip.render_pod_manifest(inf=inf, vip=vip)
    location = config.KUBEVIP_MANIFEST_FILENAME
    for vmid in plane_ids:
        ControlPlaneService.install_static_pod(api, node, vmid, location, manifest)


def InstallCmd(parser: argparse.ArgumentParser):
    parser.add_argument("plane_ids", nargs="+")
    parser.add_argument("--vip", type=str, required=True)
    parser.add_argument("--inf", "--interface", type=str, required=True)
    parser.set_defaults(func=run)
