package templates

import _ "embed"

//go:embed kubesetup-1.30.sh
var KubesetupTemplate string
