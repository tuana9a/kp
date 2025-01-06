# delete control plane

set vars

```bash
dad_id=
child_id=
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

# related

[create-control-plane.md](create-control-plane.md)
