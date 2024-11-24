package cmd

import (
	"github.com/spf13/cobra"
)

var controlPlaneCmd = &cobra.Command{
	Use:     "control-plane",
	Aliases: []string{"plane"},
	Run: func(cmd *cobra.Command, args []string) {
		// Do Stuff Here
	},
}

func init() {

}
