package apiserver

import (
	"github.com/spf13/cobra"
)

var vmid int
var flagsFile string

var ApiServerCmd = &cobra.Command{
	Use: "apiserver",
}

func init() {
	ApiServerCmd.AddCommand(addFlagsCmd)
}
