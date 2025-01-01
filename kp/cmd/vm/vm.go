package vm

import (
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/cmd/vm/agent"
	"github.com/tuana9a/kp/kp/cmd/vm/apiserver"
	"github.com/tuana9a/kp/kp/cmd/vm/cloudinit"
	"github.com/tuana9a/kp/kp/cmd/vm/config"
	"github.com/tuana9a/kp/kp/cmd/vm/disk"
	"github.com/tuana9a/kp/kp/cmd/vm/etcd"
	"github.com/tuana9a/kp/kp/cmd/vm/kubeadm"
	"github.com/tuana9a/kp/kp/cmd/vm/kubectl"
	"github.com/tuana9a/kp/kp/cmd/vm/kubesetup"
	"github.com/tuana9a/kp/kp/cmd/vm/kubevip"
	"github.com/tuana9a/kp/kp/cmd/vm/ssh"
	"github.com/tuana9a/kp/kp/cmd/vm/userdata"
)

var vmid int
var templateId int

var VirtualMachineCmd = &cobra.Command{
	Use:     "virtual-machine",
	Aliases: []string{"vm"},
}

func init() {
	VirtualMachineCmd.AddCommand(startCmd)
	VirtualMachineCmd.AddCommand(shutdownCmd)
	VirtualMachineCmd.AddCommand(deleteCmd)
	VirtualMachineCmd.AddCommand(cloneCmd)
	VirtualMachineCmd.AddCommand(disk.DiskCmd)
	VirtualMachineCmd.AddCommand(config.ConfigCmd)
	VirtualMachineCmd.AddCommand(agent.AgentCmd)
	VirtualMachineCmd.AddCommand(cloudinit.CloudinitCmd)
	VirtualMachineCmd.AddCommand(userdata.UserdataCmd)
	VirtualMachineCmd.AddCommand(ssh.SshCmd)
	VirtualMachineCmd.AddCommand(kubeadm.KubeadmCmd)
	VirtualMachineCmd.AddCommand(kubesetup.KubesetupCmd)
	VirtualMachineCmd.AddCommand(apiserver.ApiServerCmd)
	VirtualMachineCmd.AddCommand(etcd.EtcdCmd)
	VirtualMachineCmd.AddCommand(kubevip.KubevipCmd)
	VirtualMachineCmd.AddCommand(kubectl.KubectlCmd)
}
