import argparse

from kp import error
from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api, parse_ifconfig


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    lb_id = args.lb_id
    plane_id = args.plane_id
    pod_cidr = args.pod_cidr
    svc_cidr = args.svc_cidr
    lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
    if not lb_ifconfig0:
        raise error.SafeException("can not detect lb ip for control_plane_endpoint")
    lb_ip = parse_ifconfig(lb_ifconfig0)
    ControlPlaneService.init(api,
                             node,
                             plane_id,
                             control_plane_endpoint=lb_ip,
                             pod_cidr=pod_cidr,
                             svc_cidr=svc_cidr)


def InitCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--lb-id", type=int, required=True)
    parser.add_argument("--plane-id", type=int, required=True)
    parser.add_argument("--pod-cidr", type=str, required=True)
    parser.add_argument("--svc-cidr", type=str, required=True)
    parser.set_defaults(func=run)
