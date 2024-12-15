package vm

import (
	"context"
	"fmt"

	"github.com/luthermonson/go-proxmox"
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/util"
)

var cloneCmd = &cobra.Command{
	Use: "clone",
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

		templateVm, err := pveNode.VirtualMachine(ctx, templateId)
		if err != nil {
			fmt.Println("Error when getting template vm", err)
			return
		}

		_, task, err := templateVm.Clone(ctx, &proxmox.VirtualMachineCloneOptions{
			NewID: vmid,
		})
		if err != nil {
			fmt.Println("Error when cloning vm", err)
			return
		}
		_, completed, _ := task.WaitForCompleteStatus(ctx, 30)
		fmt.Println("Wait for clone task", completed)
		if !completed {
			fmt.Println("Can not complete cloning vm", task.ID)
			return
		}
	},
}

func init() {
	cloneCmd.Flags().IntVar(&templateId, "template-id", 0, "template-id (required)")
	cloneCmd.MarkFlagRequired("template-id")
	cloneCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	cloneCmd.MarkFlagRequired("vmid")
}
