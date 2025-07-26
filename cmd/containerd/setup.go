package containerd

import (
	"bytes"
	"context"
	"fmt"
	"text/template"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/payload"
	"github.com/tuana9a/kp/templates"
	"github.com/tuana9a/kp/util"
	"go.uber.org/zap"
)

var setupCmd = &cobra.Command{
	Use: "setup",
	Run: func(cmd *cobra.Command, args []string) {
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		cfg := util.LoadConfig(configPath)
		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		_, err := proxmoxClient.Version(context.Background())
		if err != nil {
			panic(err)
		}
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
		vmV2 := model.CreateVirtualMachineV2(vm, *proxmoxClient)
		var buffer bytes.Buffer
		t, err := template.New("containerd-setup").Parse(templates.ContainerdSetupTemplate)
		if err != nil {
			util.Log().Error("", zap.Error(err))
		}
		t.Execute(&buffer, payload.ContainerdSetupTemplate{
			Envs: []string{
				"http_proxy=http://proxy.vhost.vn:8080",                                  // TODO: variable later
				"HTTP_PROXY=http://proxy.vhost.vn:8080",                                  // TODO: variable later
				"https_proxy=http://proxy.vhost.vn:8080",                                 // TODO: variable later
				"HTTPS_PROXY=http://proxy.vhost.vn:8080",                                 // TODO: variable later
				"no_proxy=localhost,127.0.0.1,192.168.0.0/16,10.244.0.0/8,10.233.0.0/16", // TODO: variable later
				"NO_PROXY=localhost,127.0.0.1,192.168.0.0/16,10.244.0.0/8,10.233.0.0/16", // TODO: variable later
			},
		})
		content := buffer.String()
		fmt.Println("write containerd setup script")
		fmt.Println(content)
		err = vmV2.AgentFileWrite(ctx, constants.ContainerdSetupScriptPath, content)
		if err != nil {
			fmt.Println("error when agent file write containerd setup script")
			return
		}

		fmt.Println("chmod containerd setup script")
		pid, err := vmV2.AgentExec(ctx, []string{"chmod", "+x", constants.ContainerdSetupScriptPath}, "")
		if err != nil {
			// TODO
		}
		status, err := vmV2.WaitForAgentExecExit(ctx, pid, 5)
		if err != nil {
			// TODO
		}
		fmt.Println("chmod containerd setup script status", status)

		fmt.Println("run containerd setup script")
		pid, err = vmV2.AgentExec(ctx, []string{constants.ContainerdSetupScriptPath}, "")
		if err != nil {
			// TODO
		}
		status, err = vmV2.WaitForAgentExecExit(ctx, pid, timeoutSeconds)
		if err != nil {
			// TODO
		}
		fmt.Println("run containerd script status")
		fmt.Println(status.OutData)
		fmt.Println(status.ErrData)
	},
}

func init() {
	setupCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	setupCmd.MarkFlagRequired("vmid")
	setupCmd.Flags().IntVar(&timeoutSeconds, "timeout", 30*60, "")
}
