package qemu

import (
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/cmd/qemu/agent"
)

var QemuCmd = &cobra.Command{
	Use: "qemu",
}

func init() {
	QemuCmd.AddCommand(agent.AgentCmd)
}
