import argparse

import urllib3

from kp import util
from kp.client.pve import PveApi
from kp.cmd.plane.etcd.snapshot.save import SaveCmd
from kp.util.log import log


def SnapshotCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    SaveCmd(subparsers.add_parser("save"))
