import argparse

from kp.cmd.plane.alone import StandaloneCmd
from kp.cmd.plane.backup import BackupCmd
from kp.cmd.plane.child import ChildCmd
from kp.cmd.plane.dad import DadCmd
from kp.cmd.plane.etcd import EtcdCmd
from kp.cmd.plane.kubeconfig import KubeconfigCmd
from kp.cmd.plane.kubevip import KubevipCmd
from kp.cmd.plane.restore import RestoreCmd


def ControlPlaneCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    StandaloneCmd(subparsers.add_parser("standalone", aliases=["alone"]))
    ChildCmd(subparsers.add_parser("child"))
    DadCmd(subparsers.add_parser("dad"))
    EtcdCmd(subparsers.add_parser("etcd"))
    KubevipCmd(subparsers.add_parser("kubevip"))
    KubeconfigCmd(subparsers.add_parser("kubeconfig"))
    BackupCmd(subparsers.add_parser("backup"))
    RestoreCmd(subparsers.add_parser("restore"))
