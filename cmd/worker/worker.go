package worker

import (
	"github.com/spf13/cobra"
)

var WorkerCmd = &cobra.Command{
	Use:     "worker",
	Aliases: []string{"wk"},
	Run: func(cmd *cobra.Command, args []string) {
		// Do Stuff Here
	},
}

var deleteCmd = &cobra.Command{
	Use:     "delete",
	Aliases: []string{"del", "remove", "rm"},
	Run: func(cmd *cobra.Command, args []string) {

	},
}

var upgradeCmd = &cobra.Command{
	Use: "upgrade",
	Run: func(cmd *cobra.Command, args []string) {

	},
}

var joinCmd = &cobra.Command{
	Use: "join",
	Run: func(cmd *cobra.Command, args []string) {

	},
}

func init() {
	WorkerCmd.AddCommand(createCmd)
	WorkerCmd.AddCommand(deleteCmd)
	WorkerCmd.AddCommand(upgradeCmd)
	WorkerCmd.AddCommand(joinCmd)
}
