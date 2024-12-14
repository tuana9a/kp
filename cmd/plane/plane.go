package plane

import (
	"github.com/spf13/cobra"

	"github.com/tuana9a/kp/cmd/plane/apiserver"
)

var ControlPlaneCmd = &cobra.Command{
	Use:     "control-plane",
	Aliases: []string{"plane"},
}

func init() {
	ControlPlaneCmd.AddCommand(apiserver.ApiServerCmd)
}
