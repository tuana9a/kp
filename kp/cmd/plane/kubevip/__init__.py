import argparse

from kp.cmd.plane.kubevip.install import InstallCmd
from kp.cmd.plane.kubevip.uninstall import UninstallCmd


def KubevipCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    InstallCmd(subparsers.add_parser("install"))
    UninstallCmd(subparsers.add_parser("uninstall"))
