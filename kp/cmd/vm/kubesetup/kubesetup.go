package kubesetup

import (
	"github.com/spf13/cobra"
)

var vmid int

var timeoutSeconds int

var KubesetupCmd = &cobra.Command{
	Use: "kubesetup",
}

func init() {
	KubesetupCmd.AddCommand(runCmd)
}
