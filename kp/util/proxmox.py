import urllib

from proxmoxer import ProxmoxAPI

from kp import config


def extract_ip(ifconfig_n: str):
    """
    Example: "ip=192.168.56.123/24,gw=192.168.56.1"
    """
    parts = ifconfig_n.split(",")
    parts = parts[0].split("=")
    parts = parts[1].split("/")
    ip = parts[0]
    return ip


def parse_ifconfig(ifconfig: str):
    """
    Example: "ip=192.168.56.123/24,gw=192.168.56.1"
    """
    parts = ifconfig.split(",")

    ip_part = parts[0]
    gw_part = parts[1]

    parts = ip_part.split("=")
    parts = parts[1].split("/")
    ip = parts[0]
    netmask = parts[1]

    parts = gw_part.split("=")
    gw_ip = parts[1]

    return {
        "ip": ip,
        "netmask": netmask,
        "gw_ip": gw_ip,
    }


def encode_sshkeys(sshkeys: str):
    if not sshkeys:
        return None
    # NOTE: https://github.com/proxmoxer/proxmoxer/issues/153
    return urllib.parse.quote(sshkeys, safe="")


def create_proxmox_api(cfg: config.Cfg):
    # TODO: verify with ca cert
    if cfg.proxmox_token_name:
        print("auth using proxmox_token")
        return ProxmoxAPI(cfg.proxmox_host,
                          port=cfg.proxmox_port,
                          user=cfg.proxmox_user,
                          token_name=cfg.proxmox_token_name,
                          token_value=cfg.proxmox_token_value,
                          verify_ssl=cfg.proxmox_verify_ssl)
    print("auth using proxmox_password")
    return ProxmoxAPI(
        cfg.proxmox_host,
        user=cfg.proxmox_user,
        password=cfg.proxmox_password,
        verify_ssl=False,
    )
