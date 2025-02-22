package member

import "github.com/spf13/cobra"

var vmid int
var dadId int
var childId int
var vmNamePrefix string

var MemberCmd = &cobra.Command{
	Use: "member",
}

func init() {
	MemberCmd.AddCommand(listCmd)
	MemberCmd.AddCommand(removeCmd)
}
