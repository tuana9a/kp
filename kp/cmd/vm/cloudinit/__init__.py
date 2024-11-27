import argparse

from kp.cmd.vm.cloudinit.wait import WaitCmd


def CloudinitCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    WaitCmd(subparsers.add_parser("wait"))
