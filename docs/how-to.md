# How to use

build it

```bash
go build -o dist/kp
```

```bash
sudo ln -sf $PWD/dist/kp /usr/local/bin/kp
```

```bash
sudo chmod +x dist/kp
```

# glossary

work node is also called data node

# create worker node

set vars

```bash
template_id=1002
dad_id=122
child_id=129
vm_net=vmbr56
vm_ip='192.168.56.29/24'
vm_gateway_ip='192.168.56.1'
vm_dns_servers="1.1.1.1 8.8.8.8" # optional
vm_cores=2
vm_mem=4096
```

steps

```bash
go run . vm clone --template-id $template_id --vmid $child_id
go run . vm disk resize --vmid $child_id --diff +30G
go run . vm config update --vmid $child_id \
--vm-cores $vm_cores \
--vm-mem $vm_mem \
--vm-net "$vm_net" \
--vm-ip "$vm_ip" \
--vm-gateway-ip "$vm_gateway_ip" \
--vm-dns-servers "$vm_dns_servers" \
--vm-start-on-boot

go run . vm start --vmid $child_id
go run . vm agent wait --vmid $child_id
go run . vm cloudinit wait --vmid $child_id
go run . vm ssh inject-authorized-keys --vmid $child_id # optional

go run . vm kubesetup run --vmid $child_id
go run . vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-worker-1.30.sh
go run . worker join --dad-id $dad_id --child-id $child_id
```

# delete worker node

set vars

```bash
dad_id=122
child_id=130
```

steps

```bash
go run . vm kubectl drain --dad-id $dad_id --child-id $child_id
go run . vm kubectl delete node --dad-id $dad_id --child-id $child_id
go run . vm shutdown --vmid $child_id
go run . vm delete --vmid $child_id
```

# create control plane

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
go run . vm clone --template-id $template_id --vmid $child_id
go run . vm disk resize --vmid $child_id --diff +18G
go run . vm config update --vmid $child_id \
--vm-cores $vm_cores \
--vm-mem $vm_mem \
--vm-net $vm_net \
--vm-ip $vm_ip \
--vm-gateway-ip $vm_gateway_ip \
--vm-dns-servers "$vm_dns_servers" \
--vm-start-on-boot

go run . vm start --vmid $child_id
go run . vm agent wait --vmid $child_id
go run . vm cloudinit wait --vmid $child_id
go run . vm ssh inject-authorized-keys --vmid $child_id # optional

go run . vm kubesetup run --vmid $child_id
go run . vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-plane-1.30.sh
go run . plane join --dad-id $dad_id --child-id $child_id
```

i'm using kubevip

```bash
vip='192.168.56.21'
inf='eth0'
go run . vm kubevip install --inf $inf --vip $vip --vmid $child_id
go run . vm kubevip status --vmid $child_id
```

# delete control plane

set vars

```bash
dad_id=122
child_id=123
```

steps

```bash
go run . vm kubectl drain --dad-id $dad_id --child-id $child_id
go run . vm kubectl delete node --dad-id $dad_id --child-id $child_id
go run . vm kubeadm reset --vmid $child_id
go run . vm etcd member remove --dad-id $dad_id --child-id $child_id # important
go run . vm etcd member list --vmid $dad_id # important
go run . vm shutdown --vmid $child_id
go run . vm delete --vmid $child_id
```
