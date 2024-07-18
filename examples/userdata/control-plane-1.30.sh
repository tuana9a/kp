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
kubernetes_version="1.29"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/Release.key | gpg --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v$kubernetes_version/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list

# Install kubernetes dependencies
apt-get update
apt install -y kubelet='1.29.6-*' kubeadm='1.29.6-*' kubectl='1.29.6-*'

# Install etcdctl https://github.com/etcd-io/etcd/releases/
ETCD_VER=v3.5.12

# Choose either URL
GOOGLE_URL=https://storage.googleapis.com/etcd
GITHUB_URL=https://github.com/etcd-io/etcd/releases/download
DOWNLOAD_URL=${GITHUB_URL}

rm -f /opt/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /opt/etcd-${ETCD_VER} && mkdir -p /opt/etcd-${ETCD_VER}

curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /opt/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /opt/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /opt/etcd-${ETCD_VER} --strip-components=1

ln -sf /opt/etcd-${ETCD_VER}/etcd* /usr/local/bin/
