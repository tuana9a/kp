package payload

type KubesetupTemplateContainerd struct {
	Envs []string
}

type KubesetupTemplateInput struct {
	Containerd KubesetupTemplateContainerd
}
