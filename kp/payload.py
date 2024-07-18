from typing import List, Union


class VmResponse:
    def __init__(
            self,
            vmid: int,
            status: str,
            name: str = None,
            **kwargs) -> None:
        self.vmid = int(vmid)
        self.name = name
        self.status = status
        self.kwargs = kwargs
        pass

    @property
    def tags(self):
        return self.kwargs.get("tags", "")


class VmConfigResponse:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        pass

    def ifconfig(self, no: int):
        return self.kwargs.get("ipconfig" + str(no), None)
