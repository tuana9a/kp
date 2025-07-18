package authkey

import (
	"github.com/spf13/cobra"
)

var vmid int
var username string
var keyContent string

var AuthorizedKeyCmd = &cobra.Command{
	Use:     "authkey",
	Aliases: []string{"authorized-key"},
}

func init() {
	AuthorizedKeyCmd.AddCommand(viewCmd)
	AuthorizedKeyCmd.AddCommand(addCmd)
	AuthorizedKeyCmd.AddCommand(removeCmd)
}
