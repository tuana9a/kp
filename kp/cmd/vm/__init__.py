import argparse

from kp.cmd.vm.agent import AgentCmd
from kp.cmd.vm.clone import CloneCmd
from kp.cmd.vm.cloudinit import CloudinitCmd
from kp.cmd.vm.reboot import RebootCmd
from kp.cmd.vm.remove import RemoveCmd
from kp.cmd.vm.scp import ScpCmd
from kp.cmd.vm.shutdown import ShutdownVmCmd
from kp.cmd.vm.start import StartCmd
from kp.cmd.vm.update_config import UpdateConfigCmd


def VmCmd(parser: argparse.ArgumentParser):
    subparsers = parser.add_subparsers()
    AgentCmd(subparsers.add_parser("agent"))
    CloudinitCmd(subparsers.add_parser("cloudinit"))
    CloneCmd(subparsers.add_parser("clone"))
    UpdateConfigCmd(subparsers.add_parser("update-config"))
    RebootCmd(subparsers.add_parser("reboot"))
    RemoveCmd(subparsers.add_parser("remove", aliases=["rm"]))
    ScpCmd(subparsers.add_parser("scp"))
    ShutdownVmCmd(subparsers.add_parser("shutdown"))
    StartCmd(subparsers.add_parser("start"))
