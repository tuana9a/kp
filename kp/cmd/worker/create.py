import argparse
import time

import urllib3

from kp import config
from kp.client.pve import PveApi
from kp.scripts import worker as scripts
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api, encode_sshkeys


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)

    dad_id = args.dad_id
    child_id = args.child_id

    template_id = args.template_id
    vm_name_prefix = args.vm_name_prefix
    new_vm_name = vm_name_prefix + str(child_id)
    vm_cores = args.vm_cores
    vm_mem = args.vm_mem
    vm_disk_size = args.vm_disk
    vm_username = args.vm_username
    vm_password = args.vm_password
    vm_network = args.vm_net
    vm_ip = args.vm_ip
    vm_start_on_boot = args.vm_start_on_boot
    network_gw_ip = PveApi.describe_network(api, node, vm_network)["ip"]

    vm_userdata = args.vm_userdata

    PveApi.clone(api, node, template_id, child_id)

    PveApi.update_config(api, node, child_id,
                         name=new_vm_name,
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
                         tags=";".join([config.Tag.kp]))
    PveApi.resize_disk(api, node, child_id, "scsi0", vm_disk_size)

    PveApi.startup(api, node, child_id)
    PveApi.wait_for_guestagent(api, node, child_id)
    PveApi.wait_for_cloudinit(api, node, child_id)

    setup_script_location = "/usr/local/bin/setup.sh"
    content = scripts.KUBE_SETUP_WORKER_DEFAULT_SCRIPT
    PveApi.write_file(api, node, child_id, setup_script_location, content)
    PveApi.exec(api, node, child_id, f"chmod +x {setup_script_location}")
    PveApi.exec(api, node, child_id, setup_script_location)

    if vm_userdata:
        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r", encoding="utf-8") as f:
            PveApi.write_file(api, node, child_id, userdata_location, f.read())
        PveApi.exec(api, node, child_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, child_id, userdata_location)

    VmService.update_containerd_config(api, node, child_id)
    VmService.restart_containerd(api, node, child_id)

    join_cmd = ControlPlaneService.create_join_command(api, node, dad_id)
    PveApi.exec(api, node, child_id, join_cmd)


def CreateCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--child-id", type=int, required=True)
    parser.add_argument("--template-id", type=int, required=True)
    parser.add_argument("--vm-net", type=str, required=True)
    parser.add_argument("--vm-ip", type=str, required=True)
    parser.add_argument("--vm-cores", type=int, default=4)
    parser.add_argument("--vm-mem", type=int, default=8192)
    parser.add_argument("--vm-disk", type=str, default="+32G")
    parser.add_argument("--vm-name-prefix", type=str, default="i-")
    parser.add_argument("--vm-username", type=str, default="u")
    parser.add_argument("--vm-password", type=str, default=str(time.time_ns()))
    parser.add_argument("--vm-start-on-boot", type=int, default=1)
    parser.add_argument("--vm-userdata", type=str, required=False)
    parser.set_defaults(func=run)
