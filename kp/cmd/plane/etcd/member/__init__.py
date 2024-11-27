import argparse

import urllib3

from kp import util
from kp.client.pve import PveApi
from kp.cmd.plane.etcd.member.list import ListCmd
from kp.cmd.plane.etcd.member.remove import RemoveCmd
from kp.util.log import log


def MemberCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    ListCmd(subparsers.add_parser("list", aliases=["ls"]))
    RemoveCmd(subparsers.add_parser("remove", aliases=["rm"]))
