import argparse

from kp.client.pve import PveApi
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.util.cfg import load_config
from kp.util.log import log
from kp.util.proxmox import create_proxmox_api, parse_ifconfig


def run(args):
    cfg = load_config()
    lb_id = args.lb_id
    dad_id = args.dad_id
    backup_dir = args.backup_dir
    pod_cidr = args.pod_cidr
    svc_cidr = args.svc_cidr

    log.info("lb_id", lb_id, "dad_id", dad_id)
    node = cfg.proxmox_node
    api = create_proxmox_api(cfg)

    dad_vm = PveApi.find_vm_by_id(api, node, dad_id)
    lb_ifconfig0 = PveApi.current_config(api, node, lb_id).ifconfig(0)
    if not lb_ifconfig0:
        raise Exception("can not detect control_plane_endpoint")
    lb_ip = parse_ifconfig(lb_ifconfig0)["ip"]
    dad_ifconfig0 = PveApi.current_config(api, node, dad_id).ifconfig(0)
    if not dad_ifconfig0:
        raise Exception("can not detect dad ip")
    dad_ip = parse_ifconfig(dad_ifconfig0)["ip"]

    VmService.kubeadm_reset(api, node, dad_id)
    cmd = f"cp -r {backup_dir}/pki/ /etc/kubernetes/"
    PveApi.exec(api, node, dad_id, cmd)

    cmd = f"""/usr/local/bin/etcdutl snapshot restore {backup_dir}/etcd/member/snap/db \
        --name {dad_vm.name} \
        --initial-cluster {dad_vm.name}=https://{dad_ip}:2380 \
        --initial-cluster-token recovery-mode \
        --initial-advertise-peer-urls https://{dad_ip}:2380 \
        --skip-hash-check=true \
        --bump-revision 1000000000 --mark-compacted \
        --data-dir /var/lib/etcd
    """.split()
    PveApi.exec(api, node, dad_id, cmd)

    ControlPlaneService.init(api, node, dad_id, lb_ip,
                             extra_opts=["--ignore-preflight-errors=DirAvailable--var-lib-etcd"],
                             pod_cidr=pod_cidr,
                             svc_cidr=svc_cidr)


def RestoreCmd(parser: argparse.ArgumentParser):
    parser.add_argument("--lb-id", type=int, required=True)
    parser.add_argument("--dad-id", type=int, required=True)
    parser.add_argument("--backup-dir", type=str, default="/root/backup")
    parser.add_argument("--pod-cidr", type=str, required=True)
    parser.add_argument("--svc-cidr", type=str, required=True)
    parser.set_defaults(func=run)
