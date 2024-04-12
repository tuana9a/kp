import os
import time
import ipaddress

from app.ctler.node import NodeController
from app.logger import Logger
from app import util


class LbService:

    def __init__(self, nodectl: NodeController, log=Logger.DEBUG) -> None:
        self.nodectl = nodectl
        self.log = log
        pass

    def create_lb(self,
                  vm_network_name,
                  vm_template_id: int,
                  config_haproxy_filepath: str,
                  haproxy_cfg: str,
                  install_kubectl_filepath: str = None,
                  preserved_ips=[],
                  vm_id_range=[0, 9999],
                  vm_core_count=2,
                  vm_memory=4096,
                  vm_disk_size="20G",
                  vm_name_prefix="i-",
                  vm_username="u",
                  vm_password="1",
                  vm_ssh_keys=None,
                  vm_start_on_boot=1,
                  **kwargs):
        nodectl = self.nodectl
        log = self.log
        r = nodectl.describe_network(vm_network_name)
        network_interface = ipaddress.IPv4Interface(r["cidr"])
        network_gw_ip = str(network_interface.ip) or r["address"]
        vm_network = network_interface.network
        ip_pool = []
        for ip in vm_network.hosts():
            ip_pool.append(str(ip))
        preserved_ips.append(network_gw_ip)
        log.debug("preserved_ips", preserved_ips)

        new_vm_id = nodectl.new_vm_id(vm_id_range)
        new_vm_ip = nodectl.new_vm_ip(ip_pool, preserved_ips)
        new_vm_name = f"{vm_name_prefix}{new_vm_id}"

        log.info("new_vm", new_vm_id, new_vm_name, new_vm_ip)
        nodectl.clone(vm_template_id, new_vm_id)

        lbctl = nodectl.lbctl(new_vm_id)
        lbctl.update_config(
            name=new_vm_name,
            cpu="cputype=host",
            cores=vm_core_count,
            memory=vm_memory,
            ciuser=vm_username,
            cipassword=vm_password,
            sshkeys=util.ProxmoxUtil.encode_sshkeys(vm_ssh_keys),
            agent="enabled=1,fstrim_cloned_disks=1",
            net0=f"virtio,bridge={vm_network_name}",
            ipconfig0=f"ip={new_vm_ip}/24,gw={network_gw_ip}",
            onboot=vm_start_on_boot,
        )
        lbctl.resize_disk("scsi0", vm_disk_size)

        lbctl.startup()
        lbctl.wait_for_guest_agent()
        log.info("started vm", new_vm_id)

        lbctl.wait_for_cloud_init()
        log.info("waited for cloud-init", new_vm_id)

        lbctl.exec("apt install -y haproxy")

        vm_config_haproxy_location = "/usr/local/bin/config_haproxy.py"
        with open(config_haproxy_filepath, "r") as f:
            lbctl.write_file(vm_config_haproxy_location, f.read())
        lbctl.exec(f"chmod +x {vm_config_haproxy_location}")

        if not os.path.exists(haproxy_cfg):
            raise FileNotFoundError(haproxy_cfg)

        vm_haproxy_cfg_path = "/etc/haproxy/haproxy.cfg"
        with open(haproxy_cfg, "r", encoding="utf8") as f:
            lbctl.write_file(vm_haproxy_cfg_path, f.read())
            lbctl.reload_haproxy()

        if install_kubectl_filepath:
            vm_install_kubectl_location = "/usr/local/bin/install-kubectl.sh"
            with open(install_kubectl_filepath, "r") as f:
                lbctl.write_file(vm_install_kubectl_location, f.read())
            lbctl.exec(f"chmod +x {vm_install_kubectl_location}")
            lbctl.exec(vm_install_kubectl_location)

        return new_vm_id

    def roll_lb(self, old_vm_id, **kwargs):
        nodectl = self.nodectl
        log = self.log
        vmctl = nodectl.vmctl(old_vm_id)
        r = vmctl.read_file("/etc/haproxy/haproxy.cfg")
        content = r["content"]
        backup_cfg_filepath = f"/tmp/haproxy-{time.time_ns()}.cfg"
        log.info("backup", backup_cfg_filepath)
        with open(backup_cfg_filepath, "w") as f:
            f.write(content)
        vmctl.shutdown()
        vmctl.wait_for_shutdown()
        vmctl.delete()
        kwargs["haproxy_cfg"] = backup_cfg_filepath
        return self.create_lb(**kwargs)
