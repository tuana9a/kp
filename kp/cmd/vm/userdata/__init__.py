import argparse

from kp.cmd.vm.userdata.run import RunCmd


def UserdataCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    RunCmd(subparsers.add_parser("run"))
