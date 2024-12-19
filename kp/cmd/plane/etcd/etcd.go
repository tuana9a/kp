package etcd

import "github.com/spf13/cobra"

var vmid int
var dadId int
var childId int
var vmNamePrefix string

var EtcdCmd = &cobra.Command{
	Use: "etcd",
}

func init() {
	EtcdCmd.AddCommand(listMembersCmd)
	EtcdCmd.AddCommand(removeMemberCmd)
}
