import argparse

from kp.cmd.vm.agent.wait import WaitCmd


def AgentCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    WaitCmd(subparsers.add_parser("wait"))
