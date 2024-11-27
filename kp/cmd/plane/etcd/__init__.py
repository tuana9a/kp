import argparse

import urllib3

from kp import util
from kp.client.pve import PveApi
from kp.cmd.plane.etcd.endpoint import EndpointCmd
from kp.cmd.plane.etcd.member import MemberCmd
from kp.cmd.plane.etcd.snapshot import SnapshotCmd
from kp.util.log import log


def EtcdCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    EndpointCmd(subparsers.add_parser("endpoint"))
    MemberCmd(subparsers.add_parser("member"))
    SnapshotCmd(subparsers.add_parser("snapshot"))
