# sreate control plane

set vars

```bash
template_id= # ex 1002
dad_id= # ex 122
child_id= # ex 123
vm_net= # ex 'vmbr56'
vm_ip= # ex '192.168.56.23/24'
vm_gateway_ip= # ex '192.168.56.1'
vm_cores=2
vm_mem=4096
```

steps

```bash
go run . vm clone --template-id $template_id --vmid $child_id
go run . vm disk resize --vmid $child_id --diff +18G
go run . vm config update --vmid $child_id --vm-net $vm_net --vm-ip $vm_ip --vm-gateway-ip $vm_gateway_ip --vm-cores $vm_cores --vm-mem $vm_mem --vm-start-on-boot
go run . vm start --vmid $child_id
go run . vm agent wait --vmid $child_id
go run . vm cloudinit wait --vmid $child_id
go run . vm ssh inject-authorized-keys --vmid $child_id
go run . vm kubesetup run --vmid $child_id
go run . vm userdata run --vmid $child_id --vm-userdata ./examples/userdata/kube-plane-1.30.sh
go run . plane join --dad-id $dad_id --child-id $child_id
```

i'm using kubevip

```bash
vip= # ex '192.168.56.21'
inf= # ex 'eth0'
go run . vm kubevip install --inf $inf --vip $vip --vmid $child_id
go run . vm kubevip status --vmid $child_id
```

# related

[delete-control-plane.md](delete-control-plane.md)