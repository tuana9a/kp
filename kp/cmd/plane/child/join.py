import argparse

import urllib3

from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    dad_id = args.dad_id
    child_id = args.child_id
    log.info("dad", dad_id, "child", child_id)

    ControlPlaneService.ensure_cert_dirs(api, node, child_id)
    ControlPlaneService.copy_kube_certs(api, node, dad_id, child_id)
    join_cmd = ControlPlaneService.create_join_command(api,
                                                       node,
                                                       dad_id,
                                                       is_control_plane=True)
    PveApi.exec(api, node, child_id, join_cmd)


def JoinCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--child-id", type=int, required=True)
    parser.set_defaults(func=run)
