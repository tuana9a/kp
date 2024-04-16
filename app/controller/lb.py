from app.controller.vm import VmController
from proxmoxer import ProxmoxAPI
from app.logger import Logger
from app import config


class LbVmController(VmController):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str,
                 log=Logger.DEBUG) -> None:
        super().__init__(api, node, vm_id, log)

    def install_haproxy(self):
        return self.exec(["apt", "install", "-y", "haproxy"])

    def update_haproxy_config(self,
                              config_content: str,
                              config_path=config.HAPROXY_CONFIG_LOCATION):
        self.write_file(config_path, config_content)

    def reload_haproxy(self):
        self.exec(["systemctl", "reload", "haproxy"], interval_check=3)
