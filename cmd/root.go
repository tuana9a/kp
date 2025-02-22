package cmd

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/cmd/plane"
	"github.com/tuana9a/kp/cmd/vm"
	"github.com/tuana9a/kp/cmd/worker"
)

var verbose bool
var config string

var rootCmd = &cobra.Command{
	Use:   "kp",
	Short: "kp is a kubernetes proxmox cli",
	Long:  "kp is a kubernetes proxmox cli",
	Run: func(cmd *cobra.Command, args []string) {
		// Do Stuff Here
	},
}

func init() {
	defaultConfigLocation := os.Getenv("KP_CONFIG")
	if defaultConfigLocation == "" {
		defaultConfigLocation = filepath.Join(os.Getenv("HOME"), "/.kp.config.json")
	}
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().StringVarP(&config, "config", "c", defaultConfigLocation, "verbose output")
	rootCmd.AddCommand(worker.WorkerCmd)
	rootCmd.AddCommand(vm.VirtualMachineCmd)
	rootCmd.AddCommand(plane.ControlPlaneCmd)
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
