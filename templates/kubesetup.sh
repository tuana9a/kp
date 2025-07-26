#!/bin/bash

set -exo pipefail

# Setup container runtime https://kubernetes.io/docs/setup/production-environment/container-runtimes/
cat << EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

# Sysctl params required by kube, params persist across reboots
cat << EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

# Apply sysctl params without reboot
sysctl --system

# k8s Prerequisites
apt install -y gnupg2

kubernetes_version="1.30"
kubernetes_version_patch="1.30.6"

# Add the repository for k8s
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/Release.key | gpg --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list

# Install k8s dependencies
apt-get update
apt install -y kubelet="$kubernetes_version_patch-*" kubeadm="$kubernetes_version_patch-*" kubectl="$kubernetes_version_patch-*"
apt-mark hold kubelet kubeadm kubectl
