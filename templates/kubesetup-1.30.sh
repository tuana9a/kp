#!/bin/bash

set -exo pipefail

# Install containerd requirements
wget -q https://github.com/opencontainers/runc/releases/download/v1.1.13/runc.amd64 -O /opt/runc.amd64
install -m 755 /opt/runc.amd64 /usr/local/sbin/runc

wget -q https://github.com/containernetworking/plugins/releases/download/v1.5.1/cni-plugins-linux-amd64-v1.5.1.tgz -O /opt/cni-plugins-linux-amd64-v1.5.1.tgz
mkdir -p /opt/cni/bin
tar Cxzvf /opt/cni/bin /opt/cni-plugins-linux-amd64-v1.5.1.tgz

# Install containerd
wget -q https://github.com/containerd/containerd/releases/download/v1.7.24/containerd-1.7.24-linux-amd64.tar.gz -O /opt/containerd-1.7.24-linux-amd64.tar.gz
tar Cxzvf /usr/local /opt/containerd-1.7.24-linux-amd64.tar.gz

## Config containerd
mkdir -p /etc/containerd
cat <<EOF > /etc/containerd/config.toml
# DO NOT EDIT IF YOU DONT FEEL CONFIDENT
version = 2
[plugins]
  [plugins."io.containerd.grpc.v1.cri"]
    [plugins."io.containerd.grpc.v1.cri".registry]
      config_path = "/etc/containerd/certs.d" # spegel
    [plugins."io.containerd.grpc.v1.cri".containerd]
      discard_unpacked_layers = false # spegel
      [plugins."io.containerd.grpc.v1.cri".containerd.runtimes]
        [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
          runtime_type = "io.containerd.runc.v2" # kube
          [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
            SystemdCgroup = true # kube
EOF

# https://raw.githubusercontent.com/containerd/containerd/main/containerd.service
cat << EOF > /lib/systemd/system/containerd.service
# Copyright The containerd Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target dbus.service

[Service]
ExecStartPre=-/sbin/modprobe overlay
ExecStart=/usr/local/bin/containerd
{{range .Containerd.Envs}}Environment="{{.}}"
{{end}}
Type=notify
Delegate=yes
KillMode=process
Restart=always
RestartSec=5

# Having non-zero Limit*s causes performance problems due to accounting overhead
# in the kernel. We recommend using cgroups to do container-local accounting.
LimitNPROC=infinity
LimitCORE=infinity

# Comment TasksMax if your systemd version does not supports it.
# Only systemd 226 and above support this version.
TasksMax=infinity
OOMScoreAdjust=-999

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable containerd
systemctl restart containerd

# Setup container runtime https://kubernetes.io/docs/setup/production-environment/container-runtimes/
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

# Sysctl params required by kube, params persist across reboots
cat <<EOF | tee /etc/sysctl.d/k8s.conf
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
