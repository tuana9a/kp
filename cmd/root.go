package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/cmd/plane"
	"github.com/tuana9a/kp/cmd/vm"
	"github.com/tuana9a/kp/cmd/worker"
	"github.com/tuana9a/kp/util"
)

var verbose bool
var config string

var rootCmd = &cobra.Command{
	Use:   "kp",
	Short: "kp is a kubernetes proxmox cli",
	Long:  "kp is a kubernetes proxmox cli",
}

func init() {
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().StringVarP(&config, "config", "c", "", "config file location")
	rootCmd.AddCommand(worker.WorkerCmd)
	rootCmd.AddCommand(vm.VirtualMachineCmd)
	rootCmd.AddCommand(plane.ControlPlaneCmd)
}

func Execute() {
	util.InitLogger()
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
