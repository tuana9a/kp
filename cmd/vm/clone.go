package vm

import (
	"context"

	"github.com/luthermonson/go-proxmox"
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/util"
	"go.uber.org/zap"
)

var cloneCmd = &cobra.Command{
	Use: "clone",
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

		templateVm, err := pveNode.VirtualMachine(ctx, templateId)
		if err != nil {
			util.Log().Error("get vm error", zap.Error(err))
			return
		}

		_, task, err := templateVm.Clone(ctx, &proxmox.VirtualMachineCloneOptions{
			NewID: vmid,
		})
		if err != nil {
			util.Log().Error("clone vm error", zap.Error(err))
			return
		}
		_, completed, _ := task.WaitForCompleteStatus(ctx, 30)
		util.Log().Info("wait clone task", zap.Bool("completed", completed))
		if !completed {
			util.Log().Warn("clone vm is not completed", zap.String("taskID", task.ID))
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
