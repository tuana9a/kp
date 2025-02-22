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
var vmAuthoriedKeysFile string

var WorkerCmd = &cobra.Command{
	Use:     "worker",
	Aliases: []string{"wk"},
}

func init() {
	WorkerCmd.AddCommand(joinCmd)
}
