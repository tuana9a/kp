package kubesetup

import (
	"context"
	"fmt"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/templates"
	"github.com/tuana9a/kp/util"
)

var runCmd = &cobra.Command{
	Use: "run",
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
		vmV2 := model.CreateVirtualMachineV2(vm, *proxmoxClient)

		content := templates.KubesetupTemplate
		fmt.Println("write kubesetup script")
		fmt.Println(content)
		err = vmV2.AgentFileWrite(ctx, constants.KubesetupScriptPath, content)
		if err != nil {
			fmt.Println("error when agent file write kubesetup script")
			return
		}

		fmt.Println("chmod kubesetup script")
		pid, err := vmV2.AgentExec(ctx, []string{"chmod", "+x", constants.KubesetupScriptPath}, "")
		if err != nil {
			// TODO
		}
		status, err := vmV2.WaitForAgentExecExit(ctx, pid, 5)
		if err != nil {
			// TODO
		}
		fmt.Println("chmod kubesetup script status", status)

		fmt.Println("run kubesetup script")
		pid, err = vmV2.AgentExec(ctx, []string{constants.KubesetupScriptPath}, "")
		if err != nil {
			// TODO
		}
		status, err = vmV2.WaitForAgentExecExit(ctx, pid, timeoutSeconds)
		if err != nil {
			// TODO
		}
		fmt.Println("run kubesetup script status")
		fmt.Println(status.OutData)
		fmt.Println(status.ErrData)
	},
}

func init() {
	runCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	runCmd.MarkFlagRequired("vmid")
	runCmd.Flags().IntVar(&timeoutSeconds, "timeout", 30*60, "")
}
