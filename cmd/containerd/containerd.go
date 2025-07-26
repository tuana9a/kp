package containerd

import (
	"github.com/spf13/cobra"
)

var vmid int

var timeoutSeconds int

var ContainerdCmd = &cobra.Command{
	Use: "containerd",
}

func init() {
	ContainerdCmd.AddCommand(setupCmd)
}
