import argparse

from kp.cmd.lb.create import CreateCmd
from kp.cmd.lb.read_config import ReadConfigCmd
from kp.cmd.lb.scp_config import ScpConfigCmd
from kp.cmd.lb.update_backends import UpdateBackendsCmd


def LbCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    CreateCmd(subparsers.add_parser("create"))
    UpdateBackendsCmd(subparsers.add_parser("update"))
    ReadConfigCmd(subparsers.add_parser("read-config"))
    ScpConfigCmd(subparsers.add_parser("scp-config"))
