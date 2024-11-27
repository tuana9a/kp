import argparse

import urllib3

from kp.client.pve import PveApi
from kp.service.lb import LbService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api, parse_ifconfig


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    lb_id = args.vmid
    plane_ids = args.plane_ids
    backends = []
    for vmid in plane_ids:
        ifconfig0 = PveApi.current_config(api, node, vmid).ifconfig(0)
        if ifconfig0:
            vmip = parse_ifconfig(ifconfig0)["ip"]
            backends.append([vmid, vmip])
    content = LbService.render_haproxy_config(backends)
    # if using the roll_lb method then the backends placeholder will
    # not be there, so preserve the old haproxy.cfg
    LbService.update_haproxy_config(api, node, lb_id, content)
    LbService.reload_haproxy(api, node, lb_id)


def UpdateBackendsCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("--plane-ids", nargs="+", required=True)
    parser.set_defaults(func=run)
