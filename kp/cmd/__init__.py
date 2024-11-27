import argparse

from kp.cmd.containerd import ContainerdCmd
from kp.cmd.kubeadm import KubeadmCmd
from kp.cmd.kubelet import KubeletCmd
from kp.cmd.lb import LbCmd
from kp.cmd.plane import ControlPlaneCmd
from kp.cmd.vm import VmCmd
from kp.cmd.worker import WorkerCmd


def RootCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    ContainerdCmd(subparsers.add_parser("containerd"))
    KubeadmCmd(subparsers.add_parser("kubeadm"))
    KubeletCmd(subparsers.add_parser("kubelet"))
    LbCmd(subparsers.add_parser("loadbalancer", aliases=["lb"]))
    ControlPlaneCmd(subparsers.add_parser("control-plane", aliases=["plane"]))
    WorkerCmd(subparsers.add_parser("worker", aliases=["wk"]))
    VmCmd(subparsers.add_parser("vm"))
