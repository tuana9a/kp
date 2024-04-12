#!/bin/bash

### [OPTIONAL]

# Install etcdctl https://github.com/etcd-io/etcd/releases/
ETCD_VER=v3.5.12

# Choose either URL
GOOGLE_URL=https://storage.googleapis.com/etcd
GITHUB_URL=https://github.com/etcd-io/etcd/releases/download
DOWNLOAD_URL=${GITHUB_URL}

rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
rm -rf /tmp/etcd-${ETCD_VER} && mkdir -p /tmp/etcd-${ETCD_VER}

curl -L ${DOWNLOAD_URL}/${ETCD_VER}/etcd-${ETCD_VER}-linux-amd64.tar.gz -o /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz
tar xzvf /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz -C /tmp/etcd-${ETCD_VER} --strip-components=1
rm -f /tmp/etcd-${ETCD_VER}-linux-amd64.tar.gz

cp /tmp/etcd-${ETCD_VER}/etcd /usr/local/bin/
cp /tmp/etcd-${ETCD_VER}/etcdctl /usr/local/bin/
cp /tmp/etcd-${ETCD_VER}/etcdutl /usr/local/bin/
