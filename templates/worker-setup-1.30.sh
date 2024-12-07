#!/bin/bash

set -e

wget -q https://github.com/containerd/containerd/releases/download/v1.6.33/containerd-1.6.33-linux-amd64.tar.gz -O /opt/containerd-1.6.33-linux-amd64.tar.gz
tar Cxzvf /usr/local /opt/containerd-1.6.33-linux-amd64.tar.gz

wget -q https://raw.githubusercontent.com/containerd/containerd/main/containerd.service -O /lib/systemd/system/containerd.service
systemctl daemon-reload
systemctl enable --now containerd

wget -q https://github.com/opencontainers/runc/releases/download/v1.1.13/runc.amd64 -O /opt/runc.amd64
install -m 755 /opt/runc.amd64 /usr/local/sbin/runc

wget -q https://github.com/containernetworking/plugins/releases/download/v1.5.1/cni-plugins-linux-amd64-v1.5.1.tgz -O /opt/cni-plugins-linux-amd64-v1.5.1.tgz
mkdir -p /opt/cni/bin
tar Cxzvf /opt/cni/bin /opt/cni-plugins-linux-amd64-v1.5.1.tgz

# Setup container runtime https://kubernetes.io/docs/setup/production-environment/container-runtimes/
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

# Sysctl params required by setup, params persist across reboots
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

# Apply sysctl params without reboot
sysctl --system

# Add the repository for K8S
kubernetes_version="1.30"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/Release.key | gpg --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list

# Install kubernetes dependencies
apt-get update
apt install -y kubelet='1.30.2-*' kubeadm='1.30.2-*' kubectl='1.30.2-*'