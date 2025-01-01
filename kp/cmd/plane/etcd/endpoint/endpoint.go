package endpoint

import (
	"github.com/spf13/cobra"
)

var vmid int

var EndpointCmd = &cobra.Command{
	Use: "endpoint",
}

func init() {
	EndpointCmd.AddCommand(statusCmd)
}
