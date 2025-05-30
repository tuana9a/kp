package cloudinit

import (
	"context"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/util"
)

var waitCmd = &cobra.Command{
	Use: "wait",
	Run: func(cmd *cobra.Command, args []string) {
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		util.Sugar().Infof("configPath: %s", configPath)
		cfg := util.LoadConfig(configPath)

		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		version, err := proxmoxClient.Version(context.Background())
		if err != nil {
			util.Sugar().Errorf("test proxmox connection error %s", err)
			return
		}
		util.Sugar().Infof("proxmox-api version: %s", version.Version)
		ctx := context.Background()

		pveNode, err := proxmoxClient.Node(ctx, cfg.ProxmoxNode)
		if err != nil {
			util.Sugar().Errorf("get proxmox node error %s", err)
			return
		}

		vm, err := pveNode.VirtualMachine(ctx, vmid)
		if err != nil {
			util.Sugar().Errorf("get vm error %s", err)
			return
		}
		vmV2 := model.VirtualMachineV2{
			VirtualMachine: vm,
		}

		err = vmV2.WaitForCloudInit(ctx)
		if err != nil {
			util.Sugar().Errorf("wait for cloud init error: %s", err)
			return
		}
	},
}

func init() {
	waitCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	waitCmd.MarkFlagRequired("vmid")
}
