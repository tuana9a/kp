# kp

a kubernetes proxmox cli

# Prepare the network for vm

ssh into the proxmox host

`vim /etc/network/interfaces`

Add these line to add a new NAT network with cidr `192.168.56.1/24`

```bash
auto vmbr56
iface vmbr56 inet static
        address 192.168.56.1/24
        bridge-ports none
        bridge-stp off
        bridge-fd 0
        post-up   iptables -t nat -A POSTROUTING -s '192.168.56.0/24' -o vmbr0 -j MASQUERADE
        post-down iptables -t nat -D POSTROUTING -s '192.168.56.0/24' -o vmbr0 -j MASQUERADE
```

# Prefare vm template

Installing `qemu-guest-agent` is required

```bash
#!/bin/bash

base_img_file=jammy-server-cloudimg-amd64.img
img_file=jammy.img

wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img -O $base_img_file

cp $base_img_file $img_file

virt-customize -a $img_file --install qemu-guest-agent

img_file=jammy.img
storage=
vmid=
core_count=
mem_size=

qm create $vmid --cores ${core_count:-2} --memory ${mem_size:-2048} --scsihw virtio-scsi-pci
qm set $vmid --scsi0 $storage:0,import-from=$PWD/$img_file
qm set $vmid --ide2 $storage:cloudinit
qm set $vmid --boot order=scsi0
qm set $vmid --serial0 socket --vga serial0
qm set $vmid --name jammy
qm template $vmid
```

# Prepare the config.json

See [./app/payload.py#Cfg](./app/payload.py#Cfg)

# Code structure

```mermaid
graph TD;
  cli-->service;
  cli-->model;
  service-->model;
  service-->util;
  cli-->util;
  model-->util;
  util-->config;
  util-->logger;
  payload-->config;
  model-->payload;
  util-->payload;
  service-->payload;
  model-->config;
  service-->config;
  cli-->config;
  service-->error;
  model-->error;
  error;
```

# How to use

TODO
```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -e .
```

```bash
sudo ln -sf $(which kp) /usr/local/bin/kp
```

# Decision / Choise / Explain

immutable infrastructure

converting worker to control plane or in reverse is not straight forward, as `kubeadm reset` leave cni (network), iptables behind so instead of modifing the node just remove it and create a new one.

# Other

format code

```bash
find -type f -name '*.py' ! -path 'app/*' -path 'cli/*' -path 'tests/*' -exec autopep8 --in-place --aggressive --aggressive '{}' \;
```
