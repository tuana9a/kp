package worker

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/util"
)

var deleteCmd = &cobra.Command{
	Use:     "delete",
	Aliases: []string{"remove"},
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
		kubeVmDad := model.KubeVirtualMachine{
			VirtualMachineV2: &model.VirtualMachineV2{
				VirtualMachine: vmDad,
				ProxmoxClient:  proxmoxClient,
			},
		}

		fmt.Println("Drain node", vmChild.Name)
		status, err := kubeVmDad.DrainNode(ctx, vmChild.Name)
		if err != nil {
			fmt.Println("Error when draing node", vmChild.Name, err)
			return
		}
		fmt.Println("Drain node", vmChild.Name, "output")
		fmt.Println(status.OutData)

		fmt.Println("Delete node", vmChild.Name)
		status, err = kubeVmDad.DeleteNode(ctx, vmChild.Name)
		if err != nil {
			fmt.Println("Error when delete node", vmChild.Name, err)
			return
		}
		fmt.Println("Delete node", vmChild.Name, "output")
		fmt.Println(status.OutData)

		fmt.Println("Shutdown vm", vmChild.Name)
		task, err := vmChild.Shutdown(ctx)
		if err != nil {
			fmt.Println("Error when shutdown vm", vmChild.Name, err)
			return
		}
		_, completed, err := task.WaitForCompleteStatus(ctx, 5*60)
		if err != nil {
			fmt.Println("Error when wait for shutdown vm", vmChild.Name, err)
			return
		}
		fmt.Println("Shut down vm", vmChild.Name, "completed", completed)

		fmt.Println("Delete vm", vmChild.Name)
		task, err = vmChild.Delete(ctx)
		if err != nil {
			fmt.Println("Error when delete vm", vmChild.Name, err)
			return
		}
		_, completed, err = task.WaitForCompleteStatus(ctx, 5*60)
		if err != nil {
			fmt.Println("Error when wait for delete vm", vmChild.Name, err)
			return
		}
		fmt.Println("Delete vm", vmChild.Name, "completed", completed)
	},
}

func init() {
	deleteCmd.Flags().IntVar(&dadId, "dad-id", 0, "dad id or control plane id (required)")
	deleteCmd.MarkFlagRequired("dad-id")

	deleteCmd.Flags().IntVar(&childId, "child-id", 0, "child id or node id (required)")
	deleteCmd.MarkFlagRequired("child-id")
}
