import argparse

from kp.cmd.containerd.update_config import UpdateConfigCmd


def ContainerdCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    UpdateConfigCmd(subparsers.add_parser("update-config"))
