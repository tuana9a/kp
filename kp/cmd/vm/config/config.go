package config

import (
	"github.com/spf13/cobra"
)

var vmid int

var vmNamePrefix string
var vmNet string
var vmIp string
var vmGatewayIp string
var vmCores int
var vmMem int
var vmMemBallooned bool
var vmDnsServers string
var vmUsername string
var vmPassword string
var vmStartOnBoot bool

var ConfigCmd = &cobra.Command{
	Use:     "config",
	Aliases: []string{"cfg"},
}

func init() {
	ConfigCmd.AddCommand(updateCmd)
}
