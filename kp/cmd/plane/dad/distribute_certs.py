import argparse

import urllib3

from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    src_id = args.dad_id
    dest_id = args.child_id
    urllib3.disable_warnings()
    log.info("src", src_id, "dest", dest_id)
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    ControlPlaneService.ensure_cert_dirs(api, node, dest_id)
    ControlPlaneService.copy_kube_certs(api, node, src_id, dest_id)


def DistributeCertsCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--dad-id", type=int)
    parser.add_argument("--child-id", type=int)
    parser.set_defaults(func=run)
