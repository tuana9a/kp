package plane

import (
	"github.com/spf13/cobra"
)

var dadId int
var childId int
var timeoutSeconds int

var ControlPlaneCmd = &cobra.Command{
	Use:     "control-plane",
	Aliases: []string{"plane"},
}

func init() {
	ControlPlaneCmd.AddCommand(joinCmd)
}
