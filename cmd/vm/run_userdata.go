package vm

import (
	"context"
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/util"
)

var runUserdataCmd = &cobra.Command{
	Use: "run-userdata",
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

		blob, err := os.ReadFile(vmUserdata)
		if err != nil {
			fmt.Println("Error reading userdata file", vmUserdata)
			return
		}
		content := string(blob)
		fmt.Println("write userdata script")
		fmt.Println(content)
		err = vmV2.AgentFileWrite(ctx, constants.UserdataScriptPath, content)
		if err != nil {
			fmt.Println("error when agent file write userdata script")
			return
		}

		fmt.Println("chmod userdata script")
		pid, err := vmV2.AgentExec(ctx, []string{"chmod", "+x", constants.UserdataScriptPath}, "")
		if err != nil {
			// TODO
		}
		status, err := vmV2.WaitForAgentExecExit(ctx, pid, 5)
		if err != nil {
			// TODO
		}
		fmt.Println("chmod userdata script status", status)

		fmt.Println("run userdata script")
		pid, err = vmV2.AgentExec(ctx, []string{constants.UserdataScriptPath}, "")
		if err != nil {
			// TODO
		}
		status, err = vmV2.WaitForAgentExecExit(ctx, pid, timeoutSeconds)
		if err != nil {
			// TODO
		}
		fmt.Println("run userdata script status")
		fmt.Println(status.OutData)
		fmt.Println(status.ErrData)
	},
}

func init() {
	runUserdataCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	runUserdataCmd.MarkFlagRequired("vmid")
	runUserdataCmd.Flags().StringVar(&vmUserdata, "vm-userdata", "", "user data script for the VM (optional)")
	runUserdataCmd.MarkFlagRequired("vm-userdata")
	runUserdataCmd.Flags().IntVar(&timeoutSeconds, "timeout", 30*60, "")
}
