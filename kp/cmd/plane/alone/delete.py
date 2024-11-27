import argparse

import urllib3

from kp.client.pve import PveApi
from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    vm_id = args.vmid
    log.info("vm_id", vm_id)
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    VmService.kubeadm_reset(api, node, vm_id)
    PveApi.shutdown(api, node, vm_id)
    PveApi.wait_for_shutdown(api, node, vm_id)
    PveApi.delete_vm(api, node, vm_id)


def DeleteCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.set_defaults(func=run)
