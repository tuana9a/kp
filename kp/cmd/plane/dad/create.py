import argparse
import time

import urllib3

from kp import config, error
from kp.client.pve import PveApi
from kp.scripts import plane as scripts
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.util import kubevip
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api, encode_sshkeys, parse_ifconfig


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)

    dad_id = args.dad_id
    lb_id = args.lb_id
    template_id = args.template_id
    vip = args.vip
    vip_inf = args.vip_inf

    if not lb_id and not vip:
        raise error.SafeException("unknow type of control plane deployment, must be: --lb-id or --vip")

    vm_name_prefix = args.vm_name_prefix
    new_vm_name = vm_name_prefix + str(dad_id)
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

    pod_cidr = args.pod_cidr
    svc_cidr = args.svc_cidr

    PveApi.clone(api, node, template_id, dad_id)
    PveApi.update_config(api, node, dad_id,
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
                         tags=";".join([config.Tag.kp]),
                         )
    PveApi.resize_disk(api, node, dad_id, "scsi0", vm_disk_size)

    PveApi.startup(api, node, dad_id)
    PveApi.wait_for_guestagent(api, node, dad_id)
    PveApi.wait_for_cloudinit(api, node, dad_id)

    setup_script_location = "/usr/local/bin/setup.sh"
    content = scripts.KUBE_SETUP_CONTROL_PLANE_DEFAULT_SCRIPT
    PveApi.write_file(api, node, dad_id, setup_script_location, content)
    PveApi.exec(api, node, dad_id, f"chmod +x {setup_script_location}")
    PveApi.exec(api, node, dad_id, setup_script_location)

    if vm_userdata:
        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r", encoding="utf-8") as f:
            PveApi.write_file(api, node, dad_id, userdata_location, f.read())
        PveApi.exec(api, node, dad_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, dad_id, userdata_location)

    VmService.update_containerd_config(api, node, dad_id)
    VmService.restart_containerd(api, node, dad_id)
    plane_endpoint = None

    if lb_id:
        lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
        if not lb_ifconfig0:
            raise error.SafeException("can not detect control_plane_endpoint")
        lb_ip = parse_ifconfig(lb_ifconfig0)["ip"]
        plane_endpoint = lb_ip

    if vip:
        kubevip_manifest = kubevip.render_pod_manifest(inf=vip_inf, vip=vip)
        ControlPlaneService.install_static_pod(api, node, dad_id, config.KUBEVIP_MANIFEST_FILENAME, kubevip_manifest)
        plane_endpoint = vip

    ControlPlaneService.init(api,
                             node,
                             dad_id,
                             control_plane_endpoint=plane_endpoint,
                             pod_cidr=pod_cidr,
                             svc_cidr=svc_cidr)
    return dad_id


def CreateCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--lb-id", type=int, required=False)
    parser.add_argument("--vip", type=str, required=False)
    parser.add_argument("--vip-inf", type=str, default="eth0")

    parser.add_argument("--template-id", type=int, required=True)
    parser.add_argument("--vm-net", type=str, required=True)
    parser.add_argument("--vm-ip", type=str, required=True)
    parser.add_argument("--vm-cores", type=int, default=2)
    parser.add_argument("--vm-mem", type=int, default=4096)
    parser.add_argument("--vm-disk", type=str, default="+20G")
    parser.add_argument("--vm-name-prefix", type=str, default="i-")
    parser.add_argument("--vm-username", type=str, default="u")
    parser.add_argument("--vm-password", type=str, default=str(time.time_ns()))
    parser.add_argument("--vm-start-on-boot", type=int, default=1)
    parser.add_argument("--vm-userdata", type=str, required=False)

    parser.add_argument("--pod-cidr", type=str, required=True)
    parser.add_argument("--svc-cidr", type=str, required=True)
    parser.set_defaults(func=run)
