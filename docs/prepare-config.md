# prepare config

default lookup location `$HOME/.kp.config.json`

```json
{
    "proxmox_verify_ssl": false,
    "proxmox_node": "xeno",
    "proxmox_host": "192.168.56.1",
    "proxmox_port": 8006,
    "proxmox_user": "root@pam",
    "proxmox_token_name": "kp",
    "proxmox_token_id": "root@pam!kp",
    "proxmox_token_value": "uuidv4",
    "vm_id_range": [
        121,
        140
    ],
    "vm_preserved_ips": [
        "192.168.56.1",
        "192.168.56.2",
        "192.168.56.3",
        "192.168.56.4",
        "192.168.56.5",
        "192.168.56.6",
        "192.168.56.7",
        "192.168.56.8",
        "192.168.56.9",
        "192.168.56.10",
        "192.168.56.11",
        "192.168.56.12",
        "192.168.56.13",
        "192.168.56.14",
        "192.168.56.15",
        "192.168.56.16",
        "192.168.56.17",
        "192.168.56.18",
        "192.168.56.19",
        "192.168.56.20"
    ],
    "vm_ssh_keys": "ssh-rsa whatever ilove@u",
    "pod_cidr": "10.244.0.0/16",
    "svc_cidr": "10.233.0.0/16",
    "log_level": "debug"
}
```