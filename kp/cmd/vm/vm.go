package vm

import (
	"github.com/spf13/cobra"
)

var vmid int
var templateId int

var vmResizeDisk string

var vmNamePrefix string
var vmNet string
var vmIp string
var vmGatewayIp string
var vmCores int
var vmMem int
var vmMemBallooned bool
var vmUsername string
var vmPassword string
var vmStartOnBoot bool
var vmUserdata string
var vmAuthoriedKeysFile string

var timeoutSeconds int

var VirtualMachineCmd = &cobra.Command{
	Use:     "virtual-machine",
	Aliases: []string{"vm"},
}

func init() {
	VirtualMachineCmd.AddCommand(startCmd)
	VirtualMachineCmd.AddCommand(shutdownCmd)
	VirtualMachineCmd.AddCommand(deleteCmd)
	VirtualMachineCmd.AddCommand(cloneCmd)
	VirtualMachineCmd.AddCommand(resizeDiskCmd)
	VirtualMachineCmd.AddCommand(updateConfigCmd)
	VirtualMachineCmd.AddCommand(waitAgentCmd)
	VirtualMachineCmd.AddCommand(waitCloudinitCmd)
	VirtualMachineCmd.AddCommand(runUserdataCmd)
	VirtualMachineCmd.AddCommand(injectAuthorizedKeysCmd)
}
