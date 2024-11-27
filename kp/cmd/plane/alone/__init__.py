import argparse
import time

import urllib3

from kp import config, util
from kp.client.pve import PveApi
from kp.cmd.plane.alone.create import CreateCmd
from kp.cmd.plane.alone.delete import DeleteCmd
from kp.scripts import plane as scripts
from kp.service.plane import ControlPlaneService
from kp.service.vm import VmService
from kp.util.log import log


def StandaloneCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    CreateCmd(subparsers.add_parser("create"))
    DeleteCmd(subparsers.add_parser("delete", aliases=["remove", "rm"]))
