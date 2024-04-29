from app.model.vm import Vm
from proxmoxer import ProxmoxAPI
from app import config


class LbVm(Vm):

    def __init__(self,
                 api: ProxmoxAPI,
                 node: str,
                 vm_id: str) -> None:
        super().__init__(api, node, vm_id)

    def install_haproxy(self):
        return self.exec(["apt", "install", "-y", "haproxy"])

    def read_haproxy_config(self,
                            config_path=config.HAPROXY_CONFIG_LOCATION):
        return self.read_file(config_path)

    def update_haproxy_config(self,
                              config_content: str,
                              config_path=config.HAPROXY_CONFIG_LOCATION):
        self.write_file(config_path, config_content)

    def reload_haproxy(self):
        self.exec(["systemctl", "reload", "haproxy"], interval_check=3)
