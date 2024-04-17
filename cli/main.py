import sys

from cli.core import Cmd
from cli.plane import ControlPlaneCmd
from cli.lb import LbCmd
from cli.help import TreeCmd
from cli.worker import WorkerCmd
from cli.vm import VmCmd


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
    MainCmd().run(sys.argv[1:])


if __name__ == "__main__":
    main()
