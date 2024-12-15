package plane

import (
	"github.com/spf13/cobra"

	"github.com/tuana9a/kp/kp/cmd/plane/apiserver"
	"github.com/tuana9a/kp/kp/cmd/plane/kubevip"
)

var dadId int
var childId int
var timeoutSeconds int

var ControlPlaneCmd = &cobra.Command{
	Use:     "control-plane",
	Aliases: []string{"plane"},
}

func init() {
	ControlPlaneCmd.AddCommand(apiserver.ApiServerCmd)
	ControlPlaneCmd.AddCommand(kubevip.KubevipCmd)
	ControlPlaneCmd.AddCommand(drainNodeCmd)
	ControlPlaneCmd.AddCommand(deleteNodeCmd)
	ControlPlaneCmd.AddCommand(joinCmd)
}
