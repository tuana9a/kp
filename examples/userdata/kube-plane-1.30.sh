#!/bin/bash

# https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner
apt install -y nfs-common

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