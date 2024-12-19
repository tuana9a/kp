package kubevm

import "github.com/spf13/cobra"

var vmid int

var KubevmCmd = &cobra.Command{
	Use:     "kubevm",
	Aliases: []string{"kube"},
}

func init() {
	KubevmCmd.AddCommand(resetCmd)
}
