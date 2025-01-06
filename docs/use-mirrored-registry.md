# using mirrored images

pulling images from public registry.k8s.io (in US) doesn't guaranteed speed and reliability, use your own registry.

## example using gcp artifact hub

### copying images to your own registry

```bash
kubeadm config images list | tee /tmp/images
```

example output from kubeadm `1.30.6`

```txt
registry.k8s.io/coredns/coredns:v1.11.3
registry.k8s.io/etcd:3.5.15-0
registry.k8s.io/kube-apiserver:v1.30.5
registry.k8s.io/kube-controller-manager:v1.30.5
registry.k8s.io/kube-proxy:v1.30.5
registry.k8s.io/kube-scheduler:v1.30.5
registry.k8s.io/pause:3.9
```

```bash
for i in $(cat /tmp/images); do
  new_name=$(echo $i | sed 's|registry.k8s.io|asia-southeast1-docker.pkg.dev/tuana9a/registry-k8s-io|g' | sed 's|coredns/coredns|coredns|g');
  gcrane copy $i $new_name;
done
```

### start using your own registry

edit `kubeadm-config`

```bash
kubectl -n kube-system edit cm kubeadm-config
```

edit `data.ClusterConfiguration` > `imageRepository`

```yaml
apiVersion: v1
data:
  ClusterConfiguration: |
    apiVersion: kubeadm.k8s.io/v1beta3
    certificatesDir: /etc/kubernetes/pki
    clusterName: kubernetes
    imageRepository: asia-southeast1-docker.pkg.dev/tuana9a/registry-k8s-io # HERE
    kind: ClusterConfiguration
    ...
kind: ConfigMap
metadata:
  name: kubeadm-config
  namespace: kube-system
  ...
```