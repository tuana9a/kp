package userdata

import (
	"github.com/spf13/cobra"
)

var vmid int
var vmUserdata string

var timeoutSeconds int

var UserdataCmd = &cobra.Command{
	Use: "userdata",
}

func init() {
	UserdataCmd.AddCommand(runCmd)
}
