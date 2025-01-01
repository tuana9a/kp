package etcd

import (
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/cmd/vm/etcd/endpoint"
	"github.com/tuana9a/kp/kp/cmd/vm/etcd/member"
)

var EtcdCmd = &cobra.Command{
	Use: "etcd",
}

func init() {
	EtcdCmd.AddCommand(member.MemberCmd)
	EtcdCmd.AddCommand(endpoint.EndpointCmd)
}
