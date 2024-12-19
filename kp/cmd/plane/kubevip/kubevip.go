package kubevip

import (
	"github.com/spf13/cobra"
)

var inf string
var vip string
var vmid int

var KubevipCmd = &cobra.Command{
	Use:     "kubevip",
	Aliases: []string{"vip"},
}

func init() {
	KubevipCmd.AddCommand(installCmd)
}
