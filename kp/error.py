class SafeException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class NewVmIdException(SafeException):
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)


class NewVmIpException(SafeException):
    def __init__(self) -> None:
        super().__init__(self.__class__.__name__)


class VmNotFoundException(SafeException):
    def __init__(self, vm_id: int) -> None:
        super().__init__(self.__class__.__name__ + f": {vm_id}")


class CreateJoinCmdException(SafeException):
    def __init__(self, stderr: str) -> None:
        super().__init__(self.__class__.__name__ + f":\n{stderr}")
