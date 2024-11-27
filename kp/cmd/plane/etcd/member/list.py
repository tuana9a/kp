import argparse

import urllib3

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    log.info("vmid", vmid)
    opts = [
        "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
        "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
        "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
    ]
    cmd = "/usr/local/bin/etcdctl member list -w table".split()
    cmd.extend(opts)
    PveApi.exec(api, node, vmid, cmd)


def ListCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.set_defaults(func=run)
