import argparse
import time

from kp import config
from kp.client.pve import PveApi
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api, encode_sshkeys


def run(args):
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    vmid = args.vmid
    vm_name_prefix = args.vm_name_prefix
    new_vm_name = vm_name_prefix + str(vmid)
    vm_cores = args.vm_cores
    vm_mem = args.vm_mem
    vm_disk_size = args.vm_disk
    vm_username = args.vm_username
    vm_password = args.vm_password
    vm_network = args.vm_net
    vm_ip = args.vm_ip
    vm_start_on_boot = args.vm_start_on_boot
    network_gw_ip = PveApi.describe_network(api, node, vm_network)["ip"]

    if vm_disk_size:
        PveApi.resize_disk(api, node, vmid, "scsi0", vm_disk_size)
    PveApi.update_config(api, node, vmid, dict(name=new_vm_name,
                         cpu="cputype=host",
                         cores=vm_cores,
                         memory=vm_mem,
                         agent="enabled=1,fstrim_cloned_disks=1",
                         ciuser=vm_username,
                         cipassword=vm_password,
                         net0=f"virtio,bridge={vm_network}",
                         ipconfig0=f"ip={vm_ip}/24,gw={network_gw_ip}",
                         sshkeys=encode_sshkeys(cfg.vm_ssh_keys),
                         onboot=vm_start_on_boot,
                         tags=";".join([config.Tag.kp])))


def UpdateConfigCmd(parser: argparse.ArgumentParser):
    parser.add_argument("vmid", type=int)
    parser.add_argument("--vm-net", type=str, required=True)
    parser.add_argument("--vm-ip", type=str, required=True)
    parser.add_argument("--vm-cores", type=int, default=2)
    parser.add_argument("--vm-mem", type=int, default=2048)
    parser.add_argument("--vm-disk", type=str, default="")
    parser.add_argument("--vm-name-prefix", type=str, default="i-")
    parser.add_argument("--vm-username", type=str, default="u")
    parser.add_argument("--vm-password", type=str, default=str(time.time_ns()))
    parser.add_argument("--vm-start-on-boot", type=int, default=1)
    parser.set_defaults(func=run)
