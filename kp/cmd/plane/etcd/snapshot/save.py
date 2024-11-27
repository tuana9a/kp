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
    backup_dir = args.backup_dir
    log.info("vmid", vmid, "backup_dir", backup_dir)
    opts = [
        "--cacert=/etc/kubernetes/pki/etcd/ca.crt",
        "--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
        "--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
    ]
    cmd = f"mkdir -p {backup_dir}".split()
    PveApi.exec(api, node, vmid, cmd)
    cmd = f"/usr/local/bin/etcdctl snapshot save {backup_dir}/snapshot.db".split()
    cmd.extend(opts)
    PveApi.exec(api, node, vmid, cmd)


def SaveCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("--backup-dir", type=str, default="/root/backup")
    parser.set_defaults(func=run)
