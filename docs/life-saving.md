# life saving

This is my experience to fix it, not a must to do but if you're running out of idea, try it.

## how to Recover your cluster when no hope left

I have lost 2/3 control planes, quorum lost, can not access api server any more, cluster hang.

Go into your last standing master.

```bash
#!/bin/bash

sudo -i

ETCDCTL_CACERT=/etc/kubernetes/pki/etcd/ca.crt
ETCDCTL_CERT=/etc/kubernetes/pki/apiserver-etcd-client.crt
ETCDCTL_KEY=/etc/kubernetes/pki/apiserver-etcd-client.key
ETCDCTL_OPTS="--cacert=$ETCDCTL_CACERT --cert=$ETCDCTL_CERT --key=$ETCDCTL_KEY"

# check status
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS member list
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS member list -w table
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS member list -w json
ETCDCTL_API=3 etcdctl $ETCDCTL_OPTS endpoint status --cluster -w table

# backup certs
rm -r /root/pki
cp -r /etc/kubernetes/pki /root/

# backup etcd (data loss is expected)
rm -r /root/etcd
cp -r /var/lib/etcd/ /root/

# cleanup things
kubeadm reset -f

# restore the certs
cp -r /root/pki/ /etc/kubernetes/

# restore the etcd data, drop old membership data and re init again with single etcd node
# NOTE: Pod will be in Pending and kube-apiserver yelling about authenticate request if not specify "--bump-revision 1000000000 --mark-compacted"
ETCD_SNAPSHOT=/root/snapshot.db # clean snapshot using `etcdctl snapshot`
ETCD_SNAPSHOT=/root/etcd/member/snap/db # hot copy from /var/lib/etcd/member/snap/db

# amount of revison will be bumped
# etcd increase the revision every write, so most likey your snapshot is falling back if compared to the current state of the cluster
BUMP_REVISION=1000000000

NODE_NAME=i-122 # the node name that you're trying to restore to
NODE_IP=192.168.56.22 # the node ip that you're trying to restore to

etcdutl snapshot restore $ETCD_SNAPSHOT \
  --name $NODE_NAME \
  --initial-cluster $NODE_NAME=https://$NODE_IP:2380 \
  --initial-cluster-token $RANDOM \
  --initial-advertise-peer-urls https://$NODE_IP:2380 \
  --skip-hash-check=true \
  --bump-revision ${BUMP_REVISION:-1000000000} --mark-compacted \
  --data-dir /var/lib/etcd

# init the cluster again and ignore existing data in /var/lib/etcd and you're good to go with your healthy cluster
kubeadm init \
  --control-plane-endpoint='192.168.56.21' \
  --pod-network-cidr='10.244.0.0/16' \
  --service-cidr='10.233.0.0/16' \
  --ignore-preflight-errors=DirAvailable--var-lib-etcd
```

## etcd randomly switch leader, kubectl randomly failed also

so frustrating

REASON: the control plane was not removed completely, power outtage, the etcd cluster was not shutdown properly, causing one or more etcd instance becomes unstable

Let's say we have 3 control planes 122, 123, 124 and 124 is flanky. So we can think of removing it.

Go into one instance that its etcd is healthy

```bash
etcdctl member rm [member_id]
```

To remove control plane completely, please run `kubeadm reset` also.

```bash
kubeadm reset -f
```

## etcdserver timeout

https://etcd.io/docs/v3.4/tuning/

REASON: Mostly because of disk performance: I faced this issue when trying to evict a longhorn node, by evicting longhorn node, its storage (replicas, volume) got transfer to other node, which cause the disk io spike, I deploy the control plane vm and the worker vm on the same ssd sata, which make the evicting affect the etcd in the control plane vm. By moving the control plane vm to use other disk: mine nvme, the above issue is no longer seen. This thing will also happens if you deploying new deployment, helm, ... because the worker will pull the image which will make the dis io high again.
