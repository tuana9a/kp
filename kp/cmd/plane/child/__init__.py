import argparse

from kp.cmd.plane.child.create import CreateCmd
from kp.cmd.plane.child.delete import DeleteCmd
from kp.cmd.plane.child.firstupgrade import FirstUpgradeCmd
from kp.cmd.plane.child.followupgrade import FollowUpgradeCmd


def ChildCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    CreateCmd(subparsers.add_parser("create"))
    DeleteCmd(subparsers.add_parser("delete", aliases=["remove", "rm"]))
    FirstUpgradeCmd(subparsers.add_parser("first-upgrade"))
    FollowUpgradeCmd(subparsers.add_parser("follow-upgrade"))
