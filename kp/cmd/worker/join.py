import argparse

import urllib3

from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def join(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    plane_id = args.dad_id
    worker_id = args.child_id
    log.info("plane", plane_id, "worker", worker_id)
    join_cmd = ControlPlaneService.create_join_command(api, node, plane_id)
    PveApi.exec(api, node, worker_id, join_cmd)


def JoinCmd(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--child-id", type=int, required=True)
    parser.set_defaults(func=join)
