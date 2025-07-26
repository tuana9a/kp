package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/cmd/apiserver"
	"github.com/tuana9a/kp/cmd/authkey"
	"github.com/tuana9a/kp/cmd/cloudinit"
	"github.com/tuana9a/kp/cmd/containerd"
	"github.com/tuana9a/kp/cmd/etcd"
	"github.com/tuana9a/kp/cmd/kubeadm"
	"github.com/tuana9a/kp/cmd/kubectl"
	"github.com/tuana9a/kp/cmd/kubevip"
	"github.com/tuana9a/kp/cmd/plane"
	"github.com/tuana9a/kp/cmd/qemu"
	"github.com/tuana9a/kp/cmd/userdata"
	"github.com/tuana9a/kp/cmd/vm"
	"github.com/tuana9a/kp/cmd/worker"
	"github.com/tuana9a/kp/util"
)

var verbose bool
var config string
var vmid int
var timeoutSeconds int

var rootCmd = &cobra.Command{
	Use:   "kp",
	Short: "kp is a kubernetes proxmox cli",
	Long:  "kp is a kubernetes proxmox cli",
}

func init() {
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().StringVarP(&config, "config", "c", os.Getenv("KP_CONFIG"), "config file location")
	rootCmd.AddCommand(worker.WorkerCmd)
	rootCmd.AddCommand(vm.VirtualMachineCmd)
	rootCmd.AddCommand(plane.ControlPlaneCmd)
	rootCmd.AddCommand(apiserver.ApiServerCmd)
	rootCmd.AddCommand(authkey.AuthorizedKeyCmd)
	rootCmd.AddCommand(cloudinit.CloudinitCmd)
	rootCmd.AddCommand(etcd.EtcdCmd)
	rootCmd.AddCommand(kubeadm.KubeadmCmd)
	rootCmd.AddCommand(kubectl.KubectlCmd)
	rootCmd.AddCommand(kubesetupCmd)
	rootCmd.AddCommand(containerd.ContainerdCmd)
	rootCmd.AddCommand(kubevip.KubevipCmd)
	rootCmd.AddCommand(qemu.QemuCmd)
	rootCmd.AddCommand(userdata.UserdataCmd)
}

func Execute() {
	util.InitLogger()
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
