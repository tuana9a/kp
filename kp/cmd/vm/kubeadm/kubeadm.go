package kubeadm

import "github.com/spf13/cobra"

var vmid int

var KubeadmCmd = &cobra.Command{
	Use:     "kubeadm",
	Aliases: []string{"adm"},
}

func init() {
	KubeadmCmd.AddCommand(resetCmd)
}
