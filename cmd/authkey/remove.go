package authkey

import (
	"context"
	"fmt"
	"strings"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/payload"
	"github.com/tuana9a/kp/util"
	"go.uber.org/zap"
)

var removeCmd = &cobra.Command{
	Use:     "remove",
	Aliases: []string{"rm"},
	Run: func(cmd *cobra.Command, args []string) {
		ctx := context.Background()
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
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

		vmV2 := model.CreateVirtualMachineV2(vm, *proxmoxClient)
		var vmHomeDir = util.GetHomeDir(username)

		var readFileResponse payload.AgentFileRead
		err = vmV2.AgentFileRead(ctx, fmt.Sprintf("%s/.ssh/authorized_keys", vmHomeDir), &readFileResponse)
		if err != nil {
			util.Log().Error("read ~/.ssh/authorized_keys error", zap.Error(err))
			return
		}
		util.Log().Info("read ~/.ssh/authorized_keys")
		fmt.Println(readFileResponse.Content)

		authorizedKeys := strings.Split(readFileResponse.Content, "\n")
		isModified := false
		for i, line := range authorizedKeys {
			if strings.TrimSpace(line) == keyContent {
				authorizedKeys[i] = ""
				isModified = true
			}
		}
		util.Log().Info("scan keys result", zap.Bool("isModified", isModified))
		if isModified {
			err = vmV2.AgentFileWrite(ctx, fmt.Sprintf("%s/.ssh/authorized_keys", vmHomeDir), strings.Join(authorizedKeys, "\n"))
			if err != nil {
				util.Log().Error("write ~/.ssh/authorized_keys error", zap.Error(err))
			}
		}

		// double check by read that again
		err = vmV2.AgentFileRead(ctx, fmt.Sprintf("%s/.ssh/authorized_keys", vmHomeDir), &readFileResponse)
		if err != nil {
			util.Log().Error("read ~/.ssh/authorized_keys error", zap.Error(err))
			return
		}
		util.Log().Info("read ~/.ssh/authorized_keys")
		fmt.Println(readFileResponse.Content)
	},
}

func init() {
	removeCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	removeCmd.Flags().StringVarP(&username, "username", "u", "", "username (required)")
	removeCmd.Flags().StringVarP(&keyContent, "key-content", "k", "", "key content to add to authorized_keys (required)")
	removeCmd.MarkFlagRequired("vmid")
	removeCmd.MarkFlagRequired("username")
	removeCmd.MarkFlagRequired("key-content")
}
