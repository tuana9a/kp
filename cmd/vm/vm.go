package vm

import (
	"github.com/spf13/cobra"
)

var vmid int

var VirtualMachineCmd = &cobra.Command{
	Use:     "virtual-machine",
	Aliases: []string{"vm"},
}

func init() {
	VirtualMachineCmd.AddCommand(startCmd)
	VirtualMachineCmd.AddCommand(shutdownCmd)
}
