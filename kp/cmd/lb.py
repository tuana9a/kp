import urllib3
import ipaddress

from kp.service.vm import VmService
from kp.util import Cmd
from kp.client.pve import PveApi
from kp.service.lb import LbService
from kp import util
from kp import config


class LbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("lb",
                         childs=[
                             CreateLbCmd(),
                             UpdateBackendsCmd(),
                             ReadConfigCmd(),
                             ScpConfigCmd(),
                         ])


class CreateLbCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("create")

    def setup(self):
        self.parser.add_argument("lbid", type=int)
        self.parser.add_argument("--plane-ids", nargs="+")

        self.parser.add_argument("--template-id", type=int, required=True)
        self.parser.add_argument("--vm-net", type=str, required=True)
        self.parser.add_argument("--vm-ip", type=str, required=True)
        self.parser.add_argument("--vm-cores", type=int, default=1)
        self.parser.add_argument("--vm-mem", type=int, default=2048)
        self.parser.add_argument("--vm-disk", type=str, default="20G")
        self.parser.add_argument("--vm-name-prefix", type=str, default="i-")
        self.parser.add_argument("--vm-username", type=str, default="u")
        self.parser.add_argument("--vm-password", type=str, default="1")
        self.parser.add_argument("--vm-start-on-boot", type=int, default=1)

        self.parser.add_argument("--vm-userdata", type=str, required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        lb_id = self.parsed_args.lbid
        plane_ids = self.parsed_args.plane_ids
        util.log.info("lb_id", lb_id, "plane_ids", plane_ids)

        template_id = self.parsed_args.template_id
        vm_name_prefix = self.parsed_args.vm_name_prefix
        new_vm_name = vm_name_prefix + str(lb_id)
        vm_cores = self.parsed_args.vm_cores
        vm_mem = self.parsed_args.vm_mem
        vm_disk_size = self.parsed_args.vm_disk
        vm_username = self.parsed_args.vm_username
        vm_password = self.parsed_args.vm_password
        vm_network = self.parsed_args.vm_net
        vm_ip = self.parsed_args.vm_ip
        vm_start_on_boot = self.parsed_args.vm_start_on_boot
        r = PveApi.describe_network(api, node, vm_network)
        network_gw_ip = str(ipaddress.IPv4Interface(r["cidr"]).ip) \
            or r["address"]

        vm_userdata = self.parsed_args.vm_userdata

        PveApi.clone(api, node, template_id, lb_id)

        PveApi.update_config(api, node, lb_id,
                             name=new_vm_name,
                             cpu="cputype=host",
                             cores=vm_cores,
                             memory=vm_mem,
                             agent="enabled=1,fstrim_cloned_disks=1",
                             ciuser=vm_username,
                             cipassword=vm_password,
                             net0=f"virtio,bridge={vm_network}",
                             ipconfig0=f"ip={vm_ip}/24,gw={network_gw_ip}",
                             sshkeys=util.Proxmox.encode_sshkeys(cfg.vm_ssh_keys),
                             onboot=vm_start_on_boot,
                             tags=";".join([config.Tag.kp]))

        PveApi.resize_disk(api, node, lb_id, "scsi0", vm_disk_size)

        PveApi.startup(api, node, lb_id)
        PveApi.wait_for_guestagent(api, node, lb_id)
        PveApi.wait_for_cloudinit(api, node, lb_id)

        userdata_location = "/usr/local/bin/userdata.sh"
        with open(vm_userdata, "r") as f:
            PveApi.write_file(api, node, lb_id, userdata_location, f.read())
        PveApi.exec(api, node, lb_id, f"chmod +x {userdata_location}")
        PveApi.exec(api, node, lb_id, userdata_location)

        backends = []
        for vmid in plane_ids:
            ifconfig0 = PveApi.current_config(api, node, vmid).ifconfig(0)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                backends.append([vmid, vmip])
        content = LbService.render_haproxy_config(backends)
        # if using the roll_lb method then the backends placeholder will
        # not be there, so preserve the old haproxy.cfg
        LbService.update_haproxy_config(api, node, lb_id, content)
        LbService.reload_haproxy(api, node, lb_id)


class ScpConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("scp-config")

    def setup(self):
        self.parser.add_argument("vmid", type=int)
        self.parser.add_argument("path", type=str)

    def run(self):
        path = self.parsed_args.path
        vm_id = self.parsed_args.vmid
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        with open(path, "r", encoding="utf-8") as f:
            location = config.HAPROXY_CFG_PATH
            PveApi.write_file(api,
                              node,
                              vm_id,
                              location,
                              f.read())
            LbService.reload_haproxy(api, node, vm_id)


class UpdateBackendsCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("update-backends", aliases=["update-config"])

    def setup(self):
        self.parser.add_argument("--lb-id", type=int, required=True)
        self.parser.add_argument("--plane-ids", nargs="+", required=True)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        lb_id = self.parsed_args.lb_id
        plane_ids = self.parsed_args.plane_ids
        backends = []
        for vmid in plane_ids:
            ifconfig0 = PveApi.current_config(api, node, vmid).ifconfig(0)
            if ifconfig0:
                vmip = util.Proxmox.extract_ip(ifconfig0)
                backends.append([vmid, vmip])
        content = LbService.render_haproxy_config(backends)
        # if using the roll_lb method then the backends placeholder will
        # not be there, so preserve the old haproxy.cfg
        LbService.update_haproxy_config(api, node, lb_id, content)
        LbService.reload_haproxy(api, node, lb_id)


class ReadConfigCmd(Cmd):

    def __init__(self) -> None:
        super().__init__("read-config")

    def setup(self):
        self.parser.add_argument("lbid", type=int)

    def run(self):
        urllib3.disable_warnings()
        cfg = util.load_config()
        node = cfg.proxmox_node
        api = util.Proxmox.create_api_client(cfg)
        vm_id = self.parsed_args.lbid
        print(LbService.read_haproxy_config(api, node, vm_id)["content"])
