package etcd

import (
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/cmd/plane/etcd/member"
)

var vmid int
var dadId int
var childId int
var vmNamePrefix string

var EtcdCmd = &cobra.Command{
	Use: "etcd",
}

func init() {
	EtcdCmd.AddCommand(member.MemberCmd)
}
