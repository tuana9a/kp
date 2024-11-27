import argparse

from kp.cmd.plane.dad.create import CreateCmd
from kp.cmd.plane.dad.create_join_command import CreateJoinCommandCmd
from kp.cmd.plane.dad.distribute_certs import DistributeCertsCmd
from kp.cmd.plane.dad.init import InitCmd


def DadCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    CreateCmd(subparsers.add_parser("create"))
    InitCmd(subparsers.add_parser("init"))
    CreateJoinCommandCmd(subparsers.add_parser("create-join-command"))
    DistributeCertsCmd(subparsers.add_parser("distribute-certs"))
