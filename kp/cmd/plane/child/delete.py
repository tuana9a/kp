import argparse

import urllib3

from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    dad_id = args.dad_id
    child_id = args.child_id
    log.info("dad_id", dad_id, "child_id", child_id)
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    child_vm = PveApi.find_vm_by_id(api, node, child_id)

    ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
    ControlPlaneService.delete_node(api, node, dad_id, child_vm.name)
    VmService.kubeadm_reset(api, node, child_id)

    PveApi.shutdown(api, node, child_id)
    PveApi.wait_for_shutdown(api, node, child_id)
    PveApi.delete_vm(api, node, child_id)


def DeleteCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--child-id", type=int, required=True)
    parser.set_defaults(func=run)
