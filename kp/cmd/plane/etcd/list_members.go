package etcd

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/util"
)

var listMembersCmd = &cobra.Command{
	Use:     "list-members",
	Aliases: []string{"ls-members"},
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		cfg := util.LoadConfig(configPath)

		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		version, err := proxmoxClient.Version(context.Background())
		if err != nil {
			panic(err)
		}
		fmt.Println("proxmox-api version", version.Version)

		pveNode, err := proxmoxClient.Node(ctx, cfg.ProxmoxNode)
		if err != nil {
			fmt.Println("Error when getting proxmox node", err)
			return
		}

		vm, err := pveNode.VirtualMachine(ctx, vmid)
		if err != nil {
			fmt.Println("Error when getting vm", vmid, err)
			return
		}
		vmV2 := &model.VirtualMachineV2{
			VirtualMachine: vm,
			ProxmoxClient:  proxmoxClient,
		}
		kubeVm := model.KubeVirtualMachine{
			VirtualMachineV2: vmV2,
		}

		command := []string{
			"/usr/local/bin/etcdctl",
			"--cacert=/etc/kubernetes/pki/etcd/ca.crt",
			"--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
			"--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
			"member",
			"list",
		}

		fmt.Println("exec", vm.Name, command)
		pid, err := kubeVm.AgentExec(ctx, command, "")
		if err != nil {
			fmt.Println("Error when exec", vm.Name, command, err)
			return
		}
		status, err := kubeVm.WaitForAgentExecExit(ctx, pid, 30)
		if err != nil {
			fmt.Println("Error when wait for exec exit", err)
			return
		}
		fmt.Println("Exec", vm.Name, "stdout")
		fmt.Println(status.OutData)
		if status.ExitCode != 0 {
			fmt.Println("Exit non zero")
			fmt.Println(status.ErrData)
			return
		}
	},
}

func init() {
	listMembersCmd.Flags().IntVar(&vmid, "vmid", 0, "")
	listMembersCmd.MarkFlagRequired("vmid")
}
