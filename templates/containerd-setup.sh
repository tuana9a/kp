#!/bin/bash

set -exo pipefail

# Install runc
if [[ ! -f "/opt/runc.amd64" ]]; then
  wget -q https://github.com/opencontainers/runc/releases/download/v1.1.13/runc.amd64 -O /opt/runc.amd64
  install -m 755 /opt/runc.amd64 /usr/local/sbin/runc
fi

# Install cni
if [[ ! -f "/opt/cni-plugins-linux-amd64-v1.5.1.tgz" ]]; then
  wget -q https://github.com/containernetworking/plugins/releases/download/v1.5.1/cni-plugins-linux-amd64-v1.5.1.tgz -O /opt/cni-plugins-linux-amd64-v1.5.1.tgz
fi

mkdir -p /opt/cni/bin
tar Cxzvf /opt/cni/bin /opt/cni-plugins-linux-amd64-v1.5.1.tgz

# Install containerd
if [[ ! -f "/opt/containerd-1.7.24-linux-amd64.tar.gz" ]]; then
  wget -q https://github.com/containerd/containerd/releases/download/v1.7.24/containerd-1.7.24-linux-amd64.tar.gz -O /opt/containerd-1.7.24-linux-amd64.tar.gz
fi

tar Cxzvf /usr/local /opt/containerd-1.7.24-linux-amd64.tar.gz

# Config containerd
mkdir -p /etc/containerd
cat << EOF > /etc/containerd/config.toml
# DO NOT EDIT
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
{{range .Envs}}Environment="{{.}}"
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
systemctl restart containerd
systemctl enable containerd
