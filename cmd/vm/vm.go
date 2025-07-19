package vm

import (
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/cmd/vm/config"
	"github.com/tuana9a/kp/cmd/vm/disk"
)

var vmid int
var templateId int

var VirtualMachineCmd = &cobra.Command{
	Use:     "virtual-machine",
	Aliases: []string{"vm"},
}

func init() {
	VirtualMachineCmd.AddCommand(startCmd)
	VirtualMachineCmd.AddCommand(shutdownCmd)
	VirtualMachineCmd.AddCommand(deleteCmd)
	VirtualMachineCmd.AddCommand(cloneCmd)
	VirtualMachineCmd.AddCommand(disk.DiskCmd)
	VirtualMachineCmd.AddCommand(config.ConfigCmd)
}
