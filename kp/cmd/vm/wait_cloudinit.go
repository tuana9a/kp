package vm

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/util"
)

var waitCloudinitCmd = &cobra.Command{
	Use: "wait-cloudinit",
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
		vmV2 := model.VirtualMachineV2{
			VirtualMachine: vm,
		}

		err = vmV2.WaitForCloudInit(ctx)
		if err != nil {
			fmt.Println("ERROR wait for cloud-init", err)
		}
	},
}

func init() {
	waitCloudinitCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	waitCloudinitCmd.MarkFlagRequired("vmid")
}
