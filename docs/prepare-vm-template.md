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
