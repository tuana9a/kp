from kp.model import Cmd


class TreeCmd(Cmd):

    def __init__(self, parent: Cmd) -> None:
        super().__init__("tree", parent=parent)

    def run(self):
        self.parent.tree()
