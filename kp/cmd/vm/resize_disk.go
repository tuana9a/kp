package vm

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/util"
)

var resizeDiskCmd = &cobra.Command{
	Use: "resize-disk",
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

		err = vm.ResizeDisk(ctx, "scsi0", vmResizeDisk)
		if err != nil {
			fmt.Println("Error when resize disk child vm", vmid, err)
			return
		}
	},
}

func init() {
	resizeDiskCmd.Flags().IntVar(&vmid, "vmid", 0, "")
	resizeDiskCmd.MarkFlagRequired("vmid")
	resizeDiskCmd.Flags().StringVar(&vmResizeDisk, "vm-resize-disk", "", "") // TODO: check regex
	resizeDiskCmd.MarkFlagRequired("vm-resize-disk")
}
