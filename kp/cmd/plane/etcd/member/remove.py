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
    member_id = args.member_id
    log.info("vmid", vmid, "member_id", member_id)
    opts = [
        "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
        "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
        "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
    ]
    cmd = f"/usr/local/bin/etcdctl member remove {member_id}".split()
    cmd.extend(opts)
    PveApi.exec(api, node, vmid, cmd)


def RemoveCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("member_id", type=str)
    parser.set_defaults(func=run)
