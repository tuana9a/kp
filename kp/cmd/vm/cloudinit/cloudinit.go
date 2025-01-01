package cloudinit

import (
	"github.com/spf13/cobra"
)

var vmid int

var CloudinitCmd = &cobra.Command{
	Use: "cloudinit",
}

func init() {
	CloudinitCmd.AddCommand(waitCmd)
}
