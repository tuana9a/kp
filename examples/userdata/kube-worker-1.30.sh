#!/bin/bash

# https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner
apt install -y nfs-common

# https://longhorn.io/docs/1.7.0/deploy/install/#installation-requirements
apt-get install -y open-iscsi
systemctl start iscsid
systemctl enable iscsid
