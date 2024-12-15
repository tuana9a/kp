package plane

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/util"
)

var joinCmd = &cobra.Command{
	Use: "join",
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

		childVm, err := pveNode.VirtualMachine(ctx, childId)
		if err != nil {
			fmt.Println("Error when getting child vm", childId, err)
			return
		}
		childVmV2 := &model.VirtualMachineV2{
			VirtualMachine: childVm,
			ProxmoxClient:  proxmoxClient,
		}
		childKubeVm := &model.KubeVirtualMachine{
			VirtualMachineV2: childVmV2,
		}

		dadVm, err := pveNode.VirtualMachine(ctx, dadId)
		if err != nil {
			fmt.Println("Error when getting vm", dadId, err)
			return
		}
		dadVmV2 := &model.VirtualMachineV2{
			VirtualMachine: dadVm,
			ProxmoxClient:  proxmoxClient,
		}
		dadKubeVm := model.KubeVirtualMachine{
			VirtualMachineV2: dadVmV2,
		}

		err = childKubeVm.EnsureCertDirs(ctx)
		if err != nil {
			panic(err)
		}
		dadKubeVm.CopyKubeCerts(ctx, childKubeVm)

		fmt.Println("Create join command")
		joinCmd, err := dadKubeVm.CreateControlPlaneJoinCommand(ctx)
		fmt.Println(joinCmd)
		if err != nil {
			// TODO
		}

		fmt.Println("Exec join command")
		pid, err := childKubeVm.AgentExec(ctx, joinCmd, "")
		if err != nil {
			// TODO
		}
		status, err := childKubeVm.WaitForAgentExecExit(ctx, pid, timeoutSeconds)
		if err != nil {
			// TODO
			fmt.Println("Error when exec join command", err)
			return
		}
		fmt.Println("Exec join command status", status)
		if status.ExitCode != 0 {
			// TODO
		}
	},
}

func init() {
	joinCmd.Flags().IntVar(&dadId, "dad-id", 0, "dad id or control plane id (required)")
	joinCmd.MarkFlagRequired("dad-id")

	joinCmd.Flags().IntVar(&childId, "child-id", 0, "child id or node id (required)")
	joinCmd.MarkFlagRequired("child-id")

	joinCmd.Flags().IntVar(&timeoutSeconds, "timeout", 15*60, "child id or node id (required)")
}
