import argparse

import urllib3

from kp import template
from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.proxmox import create_proxmox_api


def run(args):
    urllib3.disable_warnings()
    cfg = load_config()
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)
    dad_id = args.dad_id
    child_id = args.child_id
    kubernetes_version_minor = ".".join(args.kubernetes_semver.split(".")[0:2])
    kubernetes_version_patch = ".".join(args.kubernetes_semver.split(".")[0:3])

    child_vm = PveApi.find_vm_by_id(api, node, child_id)

    vm_userdata = "/usr/local/bin/upgrade.sh"
    tmpl = template.UPGRADE_PLANE_SCRIPT_TEMPLATE
    userdata_content = tmpl.format(kubernetes_version_minor=kubernetes_version_minor,
                                   kubernetes_version_patch=kubernetes_version_patch)
    PveApi.write_file(api, node, child_id, vm_userdata, userdata_content)
    PveApi.exec(api, node, child_id, f"chmod +x {vm_userdata}")
    PveApi.exec(api, node, child_id, vm_userdata)
    PveApi.exec(api, node, child_id, "sudo kubeadm upgrade node".split())  # only line that diff from UpgradeFirstChildCmd

    ControlPlaneService.drain_node(api, node, dad_id, child_vm.name)
    # NOTE: with quote at package version will not work
    # Eg: apt install -y kubelet="1.29.6-*"
    #    2024-07-16 00:18:22 [DEBUG] pve-cobi 128 exec 333843 stderr
    #    E: Version '"1.29.6-*"' for 'kubelet' was not found
    #    E: Version '"1.29.6-*"' for 'kubectl' was not found
    # I think is because of shell text processing
    cmd = f"apt install -y kubelet={kubernetes_version_patch}-* kubectl={kubernetes_version_patch}-*".split()
    PveApi.exec(api, node, child_id, cmd)
    VmService.systemctl_daemon_reload(api, node, child_id)
    VmService.restart_kubelet(api, node, child_id)
    ControlPlaneService.uncordon_node(api, node, dad_id, child_vm.name)


def FollowUpgradeCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--child-id", type=int, required=True)
    parser.add_argument("--kubernetes-semver", type=str, required=True)
    parser.set_defaults(func=run)
