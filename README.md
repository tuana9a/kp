# kp

a kubernetes proxmox cli

- [life saving tips](./docs/life-saving.md)
- [create control plane](./docs/create-control-plane.md)
- [delete control plane](./docs/delete-control-plane.md)
- [create worker node (data node)](./docs/create-worker-node.md)
- [delete worker node (data node)](./docs/delete-worker-node.md)

# documentation

See folder [`docs/`](docs/) for number of docs

# immutable infrastructure

- converting worker to control plane or in reverse is not straight forward, as `kubeadm reset` leave cni (network), iptables behind so instead of modifing the node just remove it and create a new one.
- when upgrading the k8s, upgrade in-place for worker node is not a must, we can just drain it, remove it, destroy it then create a new one with installed newer k8s verion.
