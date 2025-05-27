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

var addCmd = &cobra.Command{
	Use: "add",
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

		pid, _ := vmV2.AgentExec(ctx, []string{"mkdir", "-p", fmt.Sprintf("%s/.ssh", vmHomeDir)}, "")
		status, _ := vmV2.WaitForAgentExecExit(ctx, pid, 5)
		util.Log().Info("mkdir ~/.ssh status", zap.Any("status", status))

		pid, _ = vmV2.AgentExec(ctx, []string{"chown", "-R", fmt.Sprintf("%s:%s", username, username), fmt.Sprintf("%s/.ssh", vmHomeDir)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		util.Log().Info("chown ~/.ssh status", zap.Any("status", status))

		pid, _ = vmV2.AgentExec(ctx, []string{"chmod", "-R", "700", fmt.Sprintf("%s/.ssh", vmHomeDir)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		util.Log().Info("chmod ~/.ssh status", zap.Any("status", status))

		pid, _ = vmV2.AgentExec(ctx, []string{"touch", fmt.Sprintf("%s/.ssh/authorized_keys", vmHomeDir)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		util.Log().Info("touch ~/.ssh status", zap.Any("status", status))

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
		isExisted := false
		for i, line := range authorizedKeys {
			if strings.TrimSpace(line) == "" {
				authorizedKeys[i] = keyContent
				isModified = true
				break
			}
			if strings.TrimSpace(line) == strings.TrimSpace(keyContent) {
				isExisted = true
				break
			}
		}
		util.Log().Info("scan keys result", zap.Bool("isModified", isModified), zap.Bool("isExisted", isExisted))
		if !isModified && !isExisted {
			authorizedKeys = append(authorizedKeys, keyContent)
		}

		err = vmV2.AgentFileWrite(ctx, fmt.Sprintf("%s/.ssh/authorized_keys", vmHomeDir), strings.Join(authorizedKeys, "\n"))
		if err != nil {
			util.Log().Error("write ~/.ssh/authorized_keys error", zap.Error(err))
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
	addCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	addCmd.Flags().StringVarP(&username, "username", "u", "", "username (required)")
	addCmd.Flags().StringVarP(&keyContent, "key-content", "k", "", "key content to add to authorized_keys (required)")
	addCmd.MarkFlagRequired("vmid")
	addCmd.MarkFlagRequired("username")
	addCmd.MarkFlagRequired("key-content")
}
