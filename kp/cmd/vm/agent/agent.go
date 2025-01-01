package agent

import (
	"github.com/spf13/cobra"
)

var vmid int

var timeoutSeconds int

var AgentCmd = &cobra.Command{
	Use: "agent",
}

func init() {
	AgentCmd.AddCommand(waitCmd)
}
