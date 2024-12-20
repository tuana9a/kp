# kp

a kubernetes proxmox cli

## Table of Contents

- [kp](#kp)
  - [Table of Contents](#table-of-contents)
- [Prepare the network for vm](#prepare-the-network-for-vm)
- [Prefare vm template](#prefare-vm-template)
- [Prepare the config.json](#prepare-the-configjson)
- [How to use](#how-to-use)
- [Example](#example)
  - [Creating worker node](#creating-worker-node)
  - [Delete worker node](#delete-worker-node)
  - [Creating control plane](#creating-control-plane)
  - [Install kubevip](#install-kubevip)
  - [Removing control plane](#removing-control-plane)
- [Life saving tips](#life-saving-tips)
  - [Randomly and continuously etcdserver switch leader, kubectl randomly failed also, so frustrating](#randomly-and-continuously-etcdserver-switch-leader-kubectl-randomly-failed-also-so-frustrating)
  - [Recovering your cluster when no hope left](#recovering-your-cluster-when-no-hope-left)
  - [etcdserver timeout](#etcdserver-timeout)
- [Decision / Choise / Explain](#decision--choise--explain)
  - [Immutable infrastructure](#immutable-infrastructure)

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

Install tools to build image

```bash
apt install libguestfs-tools
```

Download base image

```bash
base_img_file=debian-12-generic-amd64.qcow2
wget https://cdimage.debian.org/images/cloud/bookworm/20241201-1948/debian-12-generic-amd64-20241201-1948.qcow2 -O $base_img_file

img_file=debian.img
cp $base_img_file $img_file

# Installing `qemu-guest-agent` is required
virt-customize -a $img_file --install qemu-guest-agent

storage=local
vmid=1002
core_count=1
mem_size=1024

qm create $vmid --cores $core_count --memory $mem_size --scsihw virtio-scsi-pci
qm set $vmid --name bookworm
qm set $vmid --scsi0 $storage:0,import-from=$PWD/$img_file
qm set $vmid --ide2 $storage:cloudinit
qm set $vmid --boot order=scsi0
qm set $vmid --serial0 socket --vga serial0
qm template $vmid
```

# Prepare the config.json

See [./app/payload.py#Cfg](./app/payload.py#Cfg)

# How to use

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

build it

```bash
pyinstaller --name kp --onefile --hidden-import proxmoxer.backends --hidden-import proxmoxer.backends.https main.py
```

```bash
sudo ln -sf $PWD/dist/kp /usr/local/bin/kp
```

```bash
sudo chmod +x /usr/local/bin/kp
```

to see tree of command

```bash
kp tree
```

# Example

## Creating worker node

```bash
template_id=1002
dad_id=122
child_id=129
vm_net=vmbr56
vm_ip='192.168.56.29/24'
vm_gateway_ip='192.168.56.1'
vm_cores=4
vm_mem=8192
go run . vm clone --template-id $template_id --vmid $child_id
go run . vm disk resize --vmid $child_id --diff +30G
go run . vm config update --vmid $child_id --vm-net $vm_net --vm-ip $vm_ip --vm-gateway-ip $vm_gateway_ip --vm-cores $vm_cores --vm-mem $vm_mem --vm-start-on-boot
go run . vm start --vmid $child_id
go run . vm agent wait --vmid $child_id
go run . vm cloudinit wait --vmid $child_id
go run . vm ssh inject-authorized-keys --vmid $child_id
go run . vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-worker-1.30.sh
go run . worker join --dad-id $dad_id --child-id $child_id
```

## Delete worker node

```bash
dad_id=122
child_id=130
go run . plane drain --dad-id $dad_id --child-id $child_id
go run . plane delete-node --dad-id $dad_id --child-id $child_id
go run . vm shutdown --vmid $child_id
go run . vm delete --vmid $child_id
```

## Creating control plane

```bash
template_id=1001
dad_id=122
child_id=123
vm_net=vmbr56
vm_ip='192.168.56.23/24'
vm_gateway_ip='192.168.56.1'
vm_cores=2
vm_mem=4096
go run . vm clone --template-id $template_id --vmid $child_id
go run . vm disk resize --vmid $child_id --diff +18G
go run . vm config update --vmid $child_id --vm-net $vm_net --vm-ip $vm_ip --vm-gateway-ip $vm_gateway_ip --vm-cores $vm_cores --vm-mem $vm_mem --vm-start-on-boot
go run . vm start --vmid $child_id
go run . vm agent wait --vmid $child_id
go run . vm cloudinit wait --vmid $child_id
go run . vm ssh inject-authorized-keys --vmid $child_id
go run . vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-plane-1.30.sh
go run . plane join --dad-id $dad_id --child-id $child_id
```

## Install kubevip

```bash
vmid=122
inf=eth0
vip=192.168.56.21
go run . plane kubevip install --vmid $vmid --inf $inf --vip $vip
```

## Removing control plane

```bash
dad_id=122
child_id=124
go run . plane drain --dad-id $dad_id --child-id $child_id
go run . plane delete-node --dad-id $dad_id --child-id $child_id
go run . vm kubeadm reset --vmid $child_id
go run . plane etcd member remove --dad-id $dad_id --child-id $child_id
go run . vm shutdown --vmid $child_id
go run . vm delete --vmid $child_id
```

# Life saving tips

This is my experience to fix it, not a must to do but if you're running out of idea, try it

## Randomly and continuously etcdserver switch leader, kubectl randomly failed also, so frustrating

REASON: Power outtage, the etcd cluster was shutdown properly

Let's say we have 3 control planes 122, 123, 124

```bash
kp plane etcdctl member rm [member_id]
```

```bash
kp vm kubeadm-reset [vmid]
```

## Recovering your cluster when no hope left

REASON: lost 2/3 control planes, quorum lost, ...

```bash
#!/bin/bash

sudo -i

ETCDCTL_CACERT=/etc/kubernetes/pki/etcd/ca.crt
ETCDCTL_CERT=/etc/kubernetes/pki/apiserver-etcd-client.crt
ETCDCTL_KEY=/etc/kubernetes/pki/apiserver-etcd-client.key
ETCDCTL_OPTS="--cacert=$ETCDCTL_CACERT --cert=$ETCDCTL_CERT --key=$ETCDCTL_KEY"

# check status
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS member list
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS member list -w table
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS member list -w json
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS endpoint status --cluster -w table

# backup certs
rm -r /root/pki
cp -r /etc/kubernetes/pki /root/

# backup etcd (data loss is expected)
rm -r /root/etcd
cp -r /var/lib/etcd/ /root/

# cleanup things
kubeadm reset -f

# restore the certs
cp -r /root/pki/ /etc/kubernetes/

# restore the etcd data, drop old membership data and re init again with single etcd node
# NOTE: Pod will be in Pending and kube-apiserver yelling about authenticate request if not specify "--bump-revision 1000000000 --mark-compacted"
ETCD_SNAPSHOT=/root/snapshot.db # clean snapshot using `etcdctl snapshot`
ETCD_SNAPSHOT=/root/etcd/member/snap/db # hot copy from /var/lib/etcd/member/snap/db
BUMP_REVISION=1000000000 # amount of revison will be bumped, etcd increase the revision every write, so most likey your snapshot is falling back if compared to the current state of the cluster
NODE_NAME=i-122 # the node name that you're trying to restore to
NODE_IP=192.168.56.22 # the node ip that you're trying to restore to

etcdutl snapshot restore $ETCD_SNAPSHOT \
  --name $NODE_NAME \
  --initial-cluster $NODE_NAME=https://$NODE_IP:2380 \
  --initial-cluster-token $RANDOM \
  --initial-advertise-peer-urls https://$NODE_IP:2380 \
  --skip-hash-check=true \
  --bump-revision ${BUMP_REVISION:-1000000000} --mark-compacted \
  --data-dir /var/lib/etcd

# init the cluster again and ignore existing data in /var/lib/etcd and you're good to go with your healthy cluster
kubeadm init \
  --control-plane-endpoint='192.168.56.21' \
  --pod-network-cidr='10.244.0.0/16' \
  --service-cidr='10.233.0.0/16' \
  --ignore-preflight-errors=DirAvailable--var-lib-etcd
```

## etcdserver timeout

https://etcd.io/docs/v3.4/tuning/

Mostly because of disk performance: I faced this issue when trying to evict a longhorn node, by evicting longhorn node, its storage (replicas, volume) got transfer to other node, which cause the disk io spike, I deploy the control plane vm and the worker vm on the same ssd sata, which make the evicting affect the etcd in the control plane vm. By moving the control plane vm to use other disk: mine nvme, the above issue is no longer seen. This thing will also happens if you deploying new deployment, helm, ... because the worker will pull the image which will make the dis io high again.

# Decision / Choise / Explain

## Immutable infrastructure

- converting worker to control plane or in reverse is not straight forward, as `kubeadm reset` leave cni (network), iptables behind so instead of modifing the node just remove it and create a new one.
- when upgrading the k8s, upgrade in-place for worker node is not a must, we can just drain it, remove it, destroy it then create a new one with installed newer k8s verion.
