package constants

var SetupScriptPath = "/usr/local/bin/setup.sh"
var UserdataScriptPath = "/usr/local/bin/userdata.sh"
var KubesetupScriptPath = "/usr/local/bin/kubesetup.sh"

var ContainerdConfigPath = "/etc/containerd/config.toml"
var KubeadminConfigPath = "/etc/kubernetes/admin.conf"

var KubeStaticPodDir = "/etc/kubernetes/manifests/"
var KubeApiServerYamlPath = KubeStaticPodDir + "kube-apiserver.yaml"
var KubevipYamlPath = KubeStaticPodDir + "kube-vip.yaml"

var KubeCertDirs = []string{
	"/etc/kubernetes/pki/",
	"/etc/kubernetes/pki/etcd/",
}
var KubeCertPaths = []string{
	"/etc/kubernetes/pki/ca.crt",
	"/etc/kubernetes/pki/ca.key",
	"/etc/kubernetes/pki/sa.key",
	"/etc/kubernetes/pki/sa.pub",
	"/etc/kubernetes/pki/front-proxy-ca.crt",
	"/etc/kubernetes/pki/front-proxy-ca.key",
	"/etc/kubernetes/pki/etcd/ca.crt",
	"/etc/kubernetes/pki/etcd/ca.key",
}
