import argparse

from kp.cmd.worker.create import CreateCmd
from kp.cmd.worker.delete import DeleteCmd
from kp.cmd.worker.join import JoinCmd
from kp.cmd.worker.upgrade import UpgradeCmd


def WorkerCmd(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers()
    CreateCmd(subparsers.add_parser("create"))
    DeleteCmd(subparsers.add_parser("delete", aliases=["remove", "rm"]))
    JoinCmd(subparsers.add_parser("join"))
    UpgradeCmd(subparsers.add_parser("upgrade"))
