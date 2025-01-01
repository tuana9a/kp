package kubeadm

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/util"
)

var resetCmd = &cobra.Command{
	Use: "reset",
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

		fmt.Println("kubeadm reset -f", vm.Name)
		err = kubeVm.KubeadmReset(ctx)
		if err != nil {
			fmt.Println("Error when kubeadm reset -f", vm.Name, err)
			return
		}
	},
}

func init() {
	resetCmd.Flags().IntVar(&vmid, "vmid", 0, "dad id or control plane id (required)")
	resetCmd.MarkFlagRequired("vmid")
}
