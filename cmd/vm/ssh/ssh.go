package ssh

import (
	"github.com/spf13/cobra"
)

var vmid int
var vmUsername string
var vmAuthoriedKeysFile string

var SshCmd = &cobra.Command{
	Use: "ssh",
}

func init() {
	SshCmd.AddCommand(injectAuthorizedKeysCmd)
}
