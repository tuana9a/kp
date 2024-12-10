import argparse

import urllib3

from kp.service.plane import ControlPlaneService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    vm_id = args.vmid
    filepath = args.file_path
    urllib3.disable_warnings()
    log.info("vm_id", vm_id)
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    _, stdout, _ = ControlPlaneService.cat_kubeconfig(
        api, node, vm_id, filepath)
    print(stdout)


def ViewCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("-f",
                        "--file-path",
                        default="/etc/kubernetes/admin.conf")
    parser.set_defaults(func=run)