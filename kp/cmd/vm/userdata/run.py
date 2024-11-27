import argparse

from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    userdata = args.userdata
    vm_userdata = "/usr/local/bin/userdata.sh"
    with open(userdata, "r", encoding="utf-8") as f:
        PveApi.write_file(api, node, vmid, vm_userdata, f.read())
    PveApi.exec(api, node, vmid, f"chmod +x {vm_userdata}")
    PveApi.exec(api, node, vmid, vm_userdata)


def RunCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("userdata", type=str)
    parser.set_defaults(func=run)
