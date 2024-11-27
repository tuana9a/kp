import argparse

import urllib3

from kp import util
from kp.client.pve import PveApi
from kp.cmd.plane.etcd.endpoint.status import StatusCmd
from kp.util.log import log


def EndpointCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    StatusCmd(subparsers.add_parser("status"))
