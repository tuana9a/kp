import argparse

from kp.cmd.kubeadm.reset import ResetCmd


def KubeadmCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    ResetCmd(subparsers.add_parser("reset"))
