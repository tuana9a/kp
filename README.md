# kp

a kubernetes proxmox cli

# How to

## glossary

> [!NOTE]
> worker node is also called data node

## Presequisites

### (optional) Setup vm nat network

On your proxmox host.

`vim /etc/network/interfaces`

Add these line to add a new NAT network with cidr `192.168.56.1/24`

```bash
auto vmbr56
iface vmbr56 inet static
        address 192.168.56.1/24
        bridge-ports none
        bridge-stp off
        bridge-fd 0
        post-up   echo 1 > /proc/sys/net/ipv4/ip_forward
        post-up   iptables -t nat -A POSTROUTING -s '192.168.56.0/24' -o vmbr0 -j MASQUERADE
        post-down iptables -t nat -D POSTROUTING -s '192.168.56.0/24' -o vmbr0 -j MASQUERADE
        post-down echo 0 > /proc/sys/net/ipv4/ip_forward
```

### Prefare vm template

> [!NOTE]
> vm template is required at the moment and will be used by the cli to create vm

On your proxmox host.

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

grab the vm template id as it's will be used later.

## build project

```bash
go build -o dist/kp
```

```bash
sudo ln -sf $PWD/dist/kp /usr/local/bin/kp
```

```bash
sudo chmod +x dist/kp
```

## prepare config

`kp.config.json`

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

## create control plane

set vars

```bash
template_id=1002
dad_id=122
child_id=123
vm_net='vmbr56'
vm_ip='192.168.56.23/24'
vm_gateway_ip='192.168.56.1'
vm_cores=2
vm_mem=4096
```

steps

```bash
kp vm clone --template-id $template_id --vmid $child_id
kp vm disk resize --vmid $child_id --diff +18G
kp vm config update --vmid $child_id --vm-cores $vm_cores --vm-mem $vm_mem --vm-net $vm_net --vm-ip $vm_ip --vm-gateway-ip $vm_gateway_ip --vm-dns-servers "$vm_dns_servers" --vm-start-on-boot

kp vm start --vmid $child_id
kp vm agent wait --vmid $child_id
kp vm cloudinit wait --vmid $child_id
kp vm ssh inject-authorized-keys --vmid $child_id # optional

kp vm kubesetup run --vmid $child_id
kp vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-plane-1.30.sh
kp plane join --dad-id $dad_id --child-id $child_id
```

i'm using kubevip

```bash
vip='192.168.56.21'
inf='eth0'
```

```bash
kp vm kubevip install --inf $inf --vip $vip --vmid $child_id
kp vm kubevip status --vmid $child_id
```

## delete control plane

set vars

```bash
dad_id=122
child_id=123
```

steps

```bash
kp vm kubectl drain --dad-id $dad_id --child-id $child_id
kp vm kubectl delete node --dad-id $dad_id --child-id $child_id
kp vm kubeadm reset --vmid $child_id
kp vm etcd member remove --dad-id $dad_id --child-id $child_id # important
kp vm etcd member list --vmid $dad_id # important
kp vm shutdown --vmid $child_id
kp vm delete --vmid $child_id
```

## create worker node

set vars

```bash
template_id=1002
dad_id=122
child_id=129
vm_net=vmbr56
vm_ip='192.168.56.29/24'
vm_gateway_ip='192.168.56.1'
vm_dns_servers="1.1.1.1 8.8.8.8" # optional
vm_cores=4
vm_mem=8192
```

steps

```bash
kp vm clone --template-id $template_id --vmid $child_id
kp vm disk resize --vmid $child_id --diff +30G
kp vm config update --vmid $child_id --vm-cores $vm_cores --vm-mem $vm_mem --vm-net "$vm_net" --vm-ip "$vm_ip" --vm-gateway-ip "$vm_gateway_ip" --vm-dns-servers "$vm_dns_servers" --vm-start-on-boot
kp vm start --vmid $child_id
kp vm agent wait --vmid $child_id
kp vm cloudinit wait --vmid $child_id
kp vm ssh inject-authorized-keys --vmid $child_id # optional
kp vm kubesetup run --vmid $child_id
kp vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-worker-1.30.sh
kp worker join --dad-id $dad_id --child-id $child_id
```

## delete worker node

set vars

```bash
dad_id=122
child_id=130
```

steps

```bash
kp vm kubectl drain --dad-id $dad_id --child-id $child_id
kp vm kubectl delete node --dad-id $dad_id --child-id $child_id
kp vm shutdown --vmid $child_id
kp vm delete --vmid $child_id
```

# decision of choices

## immutable infrastructure

- converting worker to control plane or in reverse is not straight forward, as `kubeadm reset` leave cni (network), iptables behind so instead of modifing the node just remove it and create a new one.
- when upgrading the k8s, upgrade in-place for worker node is not a must, we can just drain it, remove it, destroy it then create a new one with installed newer k8s verion.

## using mirrored images

pulling images from public registry.k8s.io (in US) doesn't guaranteed speed and reliability, use your own registry.

## example using gcp artifact hub

copying images to your own registry

```bash
kubeadm config images list | tee /tmp/images
```

example output from kubeadm `1.30.6`

```txt
registry.k8s.io/coredns/coredns:v1.11.3
registry.k8s.io/etcd:3.5.15-0
registry.k8s.io/kube-apiserver:v1.30.5
registry.k8s.io/kube-controller-manager:v1.30.5
registry.k8s.io/kube-proxy:v1.30.5
registry.k8s.io/kube-scheduler:v1.30.5
registry.k8s.io/pause:3.9
```

```bash
for i in $(cat /tmp/images); do
  new_name=$(echo $i | sed 's|registry.k8s.io|asia-southeast1-docker.pkg.dev/tuana9a/registry-k8s-io|g' | sed 's|coredns/coredns|coredns|g');
  gcrane copy $i $new_name;
done
```

start using your own registry

edit `kubeadm-config`

```bash
kubectl -n kube-system edit cm kubeadm-config
```

edit `data.ClusterConfiguration` > `imageRepository`

```yaml
apiVersion: v1
data:
  ClusterConfiguration: |
    apiVersion: kubeadm.k8s.io/v1beta3
    certificatesDir: /etc/kubernetes/pki
    clusterName: kubernetes
    imageRepository: asia-southeast1-docker.pkg.dev/tuana9a/registry-k8s-io # HERE
    kind: ClusterConfiguration
    ...
kind: ConfigMap
metadata:
  name: kubeadm-config
  namespace: kube-system
  ...
```

# life saving

This is my experience to fix it, not a must to do but if you're running out of idea, try it.

## how to Recover your cluster when no hope left

I have lost 2/3 control planes, quorum lost, can not access api server any more, cluster hang.

Go into your last standing master.

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

# amount of revison will be bumped
# etcd increase the revision every write, so most likey your snapshot is falling back if compared to the current state of the cluster
BUMP_REVISION=1000000000

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

## etcd randomly switch leader, kubectl randomly failed also

so frustrating

REASON: the control plane was not removed completely, power outtage, the etcd cluster was not shutdown properly, causing one or more etcd instance becomes unstable

Let's say we have 3 control planes 122, 123, 124 and 124 is flanky. So we can think of removing it.

Go into one instance that its etcd is healthy

```bash
etcdctl member rm [member_id]
```

To remove control plane completely, please run `kubeadm reset` also.

```bash
kubeadm reset -f
```

## etcdserver timeout

https://etcd.io/docs/v3.4/tuning/

REASON: Mostly because of disk performance: I faced this issue when trying to evict a longhorn node, by evicting longhorn node, its storage (replicas, volume) got transfer to other node, which cause the disk io spike, I deploy the control plane vm and the worker vm on the same ssd sata, which make the evicting affect the etcd in the control plane vm. By moving the control plane vm to use other disk: mine nvme, the above issue is no longer seen. This thing will also happens if you deploying new deployment, helm, ... because the worker will pull the image which will make the dis io high again.
