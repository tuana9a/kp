import argparse

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    backup_dir = args.backup_dir
    log.info("vmid", vmid, "backup_dir", backup_dir)
    cmd = f"mkdir -p {backup_dir}".split()
    PveApi.exec(api, node, vmid, cmd)
    cmd = f"cp -r /etc/kubernetes/pki {backup_dir}"
    PveApi.exec(api, node, vmid, cmd)
    cmd = f"cp -r /var/lib/etcd/ {backup_dir}"
    PveApi.exec(api, node, vmid, cmd)


def BackupCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("--backup-dir", type=str, default="/root/backup")
    parser.set_defaults(func=run)
