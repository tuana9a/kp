package disk

import (
	"github.com/spf13/cobra"
)

var vmid int
var diff string

var DiskCmd = &cobra.Command{
	Use: "disk",
}

func init() {
	DiskCmd.AddCommand(resizeCmd)
}
