import sys

from kp.model import Cmd
from kp.cmd.plane import ControlPlaneCmd
from kp.cmd.lb import LbCmd
from kp.cmd.help import TreeCmd
from kp.cmd.worker import WorkerCmd
from kp.cmd.vm import VmCmd


class MainCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("kp",
                         childs=[
                             ControlPlaneCmd(),
                             LbCmd(),
                             WorkerCmd(),
                             VmCmd(),
                             TreeCmd(parent=self)
                         ])


def main():
    MainCmd().call(sys.argv[1:])


if __name__ == "__main__":
    main()
