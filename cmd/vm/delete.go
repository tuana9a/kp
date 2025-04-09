package vm

import (
	"context"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/util"
	"go.uber.org/zap"
)

var deleteCmd = &cobra.Command{
	Use:     "delete",
	Aliases: []string{"del", "remove", "rm"},
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

		task, err := vm.Delete(ctx)
		if err != nil {
			util.Log().Error("delete vm error", zap.Any("taskId", task.ID), zap.Error(err))
			return
		}
		status, completed, err := task.WaitForCompleteStatus(ctx, 15*60)
		if err != nil {
			util.Log().Error("wait task error", zap.Any("taskId", task.ID), zap.Error(err))
		}
		util.Log().Info("delete vm", zap.Int("vmid", vmid), zap.Bool("completed", completed), zap.Bool("status", status))
	},
}

func init() {
	deleteCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	deleteCmd.MarkFlagRequired("vmid")
}
