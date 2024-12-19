package kubevip

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/util"
)

var installCmd = &cobra.Command{
	Use: "install",
	Run: func(cmd *cobra.Command, args []string) {
		verbose, _ := cmd.Root().PersistentFlags().GetBool("verbose")
		fmt.Println("verbose: ", verbose)

		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		cfg := util.LoadConfig(configPath)

		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		version, err := proxmoxClient.Version(context.Background())
		if err != nil {
			panic(err)
		}
		fmt.Println("proxmox-api version: ", version.Version)
		ctx := context.Background()

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
		kubeVm.InstallKubevip(ctx, inf, vip)
	},
}

func init() {
	installCmd.Flags().IntVar(&vmid, "vmid", 0, "dad id or control plane id (required)")
	installCmd.MarkFlagRequired("vmid")

	installCmd.Flags().StringVar(&inf, "inf", "", "child id or node id (required)")
	installCmd.MarkFlagRequired("inf")

	installCmd.Flags().StringVar(&vip, "vip", "", "child id or node id (required)")
	installCmd.MarkFlagRequired("vip")
}
