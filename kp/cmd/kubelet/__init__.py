import argparse

from kp.cmd.kubelet.restart import RestartCmd


def KubeletCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    RestartCmd(subparsers.add_parser("restart"))
