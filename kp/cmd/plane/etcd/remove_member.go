package etcd

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/payload"
	"github.com/tuana9a/kp/kp/util"
)

var removeMemberCmd = &cobra.Command{
	Use:     "remove-member",
	Aliases: []string{"rm-member"},
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

		vm, err := pveNode.VirtualMachine(ctx, dadId)
		if err != nil {
			fmt.Println("Error when getting vm", dadId, err)
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
			"-w",
			"json",
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
		var etcdListOut payload.EtcdMemberListOut
		err = json.Unmarshal([]byte(status.OutData), &etcdListOut)
		if err != nil {
			fmt.Println("Can not unmarshal json", status.OutData)
			return
		}
		fmt.Println(etcdListOut)
		memberName := vmNamePrefix + strconv.FormatInt(int64(childId), 10)
		for _, m := range etcdListOut.Members {
			if m.Name == memberName {
				memberId := strconv.FormatUint(m.ID, 16)
				fmt.Println("Found", memberName, memberId)
				command := []string{
					"/usr/local/bin/etcdctl",
					"--cacert=/etc/kubernetes/pki/etcd/ca.crt",
					"--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
					"--key=/etc/kubernetes/pki/apiserver-etcd-client.key",
					"member",
					"remove",
					memberId,
				}
				fmt.Println("exec", vm.Name, command)
				pid, err := kubeVm.AgentExec(ctx, command, "")
				if err != nil {
					fmt.Println("Error when exec", vm.Name, command)
					return
				}
				status, err := kubeVm.WaitForAgentExecExit(ctx, pid, 30)
				if err != nil {
					fmt.Println("Error when wait for exec exit")
					return
				}
				fmt.Println("Exec", vm.Name, "stdout")
				fmt.Println(status.OutData)
				if status.ExitCode != 0 {
					fmt.Println("Exit non zero")
					fmt.Println(status.ErrData)
					return
				}
			}
		}
	},
}

func init() {
	removeMemberCmd.Flags().IntVar(&dadId, "dad-id", 0, "")
	removeMemberCmd.MarkFlagRequired("dad-id")
	removeMemberCmd.Flags().IntVar(&childId, "child-id", 0, "")
	removeMemberCmd.MarkFlagRequired("child-id")
	removeMemberCmd.Flags().StringVar(&vmNamePrefix, "vm-name-prefix", "i-", "prefix for VM names (default: i-)")
}
