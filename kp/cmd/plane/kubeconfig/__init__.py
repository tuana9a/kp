import argparse

import urllib3

from kp import util
from kp.cmd.plane.kubeconfig.download import DownloadCmd
from kp.cmd.plane.kubeconfig.view import ViewCmd
from kp.service.plane import ControlPlaneService
from kp.util.log import log


def KubeconfigCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    ViewCmd(subparsers.add_parser("view", aliases=["cat"]))
    DownloadCmd(subparsers.add_parser("download"))
