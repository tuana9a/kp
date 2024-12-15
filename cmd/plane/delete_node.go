package plane

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/util"
)

var deleteNodeCmd = &cobra.Command{
	Use: "delete-node",
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

		vmChild, err := pveNode.VirtualMachine(ctx, childId)
		if err != nil {
			fmt.Println("Error when getting child vm", childId, err)
			return
		}

		vmDad, err := pveNode.VirtualMachine(ctx, dadId)
		if err != nil {
			fmt.Println("Error when getting dad vm", dadId, err)
			return
		}
		vmDadV2 := &model.VirtualMachineV2{
			VirtualMachine: vmDad,
			ProxmoxClient:  proxmoxClient,
		}
		kubeVmDad := model.KubeVirtualMachine{
			VirtualMachineV2: vmDadV2,
		}

		fmt.Println("Delete node", vmChild.Name)
		status, err := kubeVmDad.DeleteNode(ctx, vmChild.Name)
		if err != nil {
			fmt.Println("Error when delete node", vmChild.Name, err)
			return
		}
		fmt.Println("Delete node", vmChild.Name, "output")
		fmt.Println(status.OutData)
	},
}

func init() {
	deleteNodeCmd.Flags().IntVar(&dadId, "dad-id", 0, "dad id or control plane id (required)")
	deleteNodeCmd.MarkFlagRequired("dad-id")

	deleteNodeCmd.Flags().IntVar(&childId, "child-id", 0, "child id or node id (required)")
	deleteNodeCmd.MarkFlagRequired("child-id")
}
