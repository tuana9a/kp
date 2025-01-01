package kubectl

import (
	"github.com/spf13/cobra"
)

var dadId int
var childId int

// var timeoutSeconds int

var KubectlCmd = &cobra.Command{
	Use:     "kubectl",
	Aliases: []string{"k"},
}

func init() {
	KubectlCmd.AddCommand(drainCmd)
	KubectlCmd.AddCommand(deleteCmd)
}
