#!/bin/bash

# Add Docker's official GPG key:
apt-get update
apt-get install apt-transport-https ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo "deb [arch=\"$(dpkg --print-architecture)\" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \"$(. /etc/os-release && echo $VERSION_CODENAME)\" stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update

# **NOTE**: cri: dockerd is not supported from 1.24, No need to install `docker-ce` and `docker-ce-cli`
apt install -y containerd.io
