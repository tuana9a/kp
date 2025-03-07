package vm

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/util"
)

var deleteCmd = &cobra.Command{
	Use:     "delete",
	Aliases: []string{"del", "remove", "rm"},
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
			panic(err)
		}

		task, err := vm.Delete(ctx)
		if err != nil {
			panic(err)
		}
		status, completed, err := task.WaitForCompleteStatus(ctx, 15*60)
		if err != nil {
			panic(err)
		}
		fmt.Println("delete vm", vmid, "completed", completed, "status", status)
	},
}

func init() {
	deleteCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	deleteCmd.MarkFlagRequired("vmid")
}
