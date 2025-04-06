package vm

import (
	"context"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/util"
	"go.uber.org/zap"
)

var shutdownCmd = &cobra.Command{
	Use: "shutdown",
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		util.Log().Info("configPath", zap.String("configPath", configPath))
		cfg := util.LoadConfig(configPath)

		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		version, err := proxmoxClient.Version(context.Background())
		if err != nil {
			util.Log().Error("test proxmox connection error", zap.Error(err))
			return
		}
		util.Log().Info("proxmox-api version", zap.String("proxmox_version", version.Version))

		pveNode, err := proxmoxClient.Node(ctx, cfg.ProxmoxNode)
		if err != nil {
			util.Log().Error("get proxmox node error", zap.Error(err))
			return
		}

		vm, err := pveNode.VirtualMachine(ctx, vmid)
		if err != nil {
			util.Log().Error("get vm error", zap.Error(err))
			return
		}

		task, err := vm.Shutdown(ctx)
		if err != nil {
			util.Log().Error("shutdown vm error", zap.Error(err))
			return
		}
		status, completed, err := task.WaitForCompleteStatus(ctx, 15*60)
		if err != nil {
			util.Log().Info("wait clone task", zap.Bool("completed", completed))
		}
		util.Log().Info("shutdown vm", zap.Int("vmid", vmid), zap.Bool("completed", completed), zap.Bool("status", status))
	},
}

func init() {
	shutdownCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	shutdownCmd.MarkFlagRequired("vmid")
}
