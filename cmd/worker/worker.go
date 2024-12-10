package worker

import (
	"github.com/spf13/cobra"
)

var dadId int
var childId int
var vmTemplateId int
var vmNamePrefix string
var vmNet string
var vmIp string
var vmCores int
var vmMem int
var vmDiskSize string
var vmUsername string
var vmPassword string
var vmStartOnBoot bool
var vmUserdata string
var vmAuthoriedKeysFile = "~/.ssh/id_rsa.pub"

var WorkerCmd = &cobra.Command{
	Use:     "worker",
	Aliases: []string{"wk"},
	Run: func(cmd *cobra.Command, args []string) {
		// Do Stuff Here
	},
}

var upgradeCmd = &cobra.Command{
	Use: "upgrade",
	Run: func(cmd *cobra.Command, args []string) {

	},
}

var joinCmd = &cobra.Command{
	Use: "join",
	Run: func(cmd *cobra.Command, args []string) {

	},
}

func init() {
	WorkerCmd.AddCommand(createCmd)
	WorkerCmd.AddCommand(deleteCmd)
	WorkerCmd.AddCommand(upgradeCmd)
	WorkerCmd.AddCommand(joinCmd)
}
