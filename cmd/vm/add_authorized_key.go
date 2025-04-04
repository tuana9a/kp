package vm

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/util"
)

var addAuthorizedKeyCmd = &cobra.Command{
	Use: "add-authorized-key",
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
			fmt.Println("error when getting proxmox node", err)
			return
		}

		vm, err := pveNode.VirtualMachine(ctx, vmid)
		if err != nil {
			panic(err)
		}
		vmV2 := model.CreateVirtualMachineV2(vm, *proxmoxClient)

		var vmHomeDir = util.GetHomeDir(username)

		pid, _ := vmV2.AgentExec(ctx, []string{"mkdir", "-p", fmt.Sprintf("%s/.ssh", vmHomeDir)}, "")
		status, _ := vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("mkdir ~/.ssh status", status)

		pid, _ = vmV2.AgentExec(ctx, []string{"chown", "-R", fmt.Sprintf("%s:%s", username, username), fmt.Sprintf("%s/.ssh", vmHomeDir)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("chown ~/.ssh status", status)

		pid, _ = vmV2.AgentExec(ctx, []string{"chmod", "-R", "700", fmt.Sprintf("%s/.ssh", vmHomeDir)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("chmod ~/.ssh status", status)

		fmt.Println("append ~/.ssh/authorized_keys")
		blob, err := os.ReadFile(keyFile)
		if err != nil {
			fmt.Println("Error when reading vmAuthoriedKeyFile", err)
			return
		}
		pid, _ = vmV2.AgentExec(ctx, []string{"sh", "-c", fmt.Sprintf("echo \"%s\" | tee -a %s/.ssh/authorized_keys", strings.TrimSpace(string(blob)), vmHomeDir)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("update ~/.ssh/authorized_keys status", status)

		fmt.Println("chmod ~/.ssh/authorized_keys")
		pid, _ = vmV2.AgentExec(ctx, []string{"chmod", "700", fmt.Sprintf("/home/%s/.ssh/authorized_keys", username)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("chmod ~/.ssh/authorized_keys status", status)
	},
}

func init() {
	addAuthorizedKeyCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	addAuthorizedKeyCmd.MarkFlagRequired("vmid")
	addAuthorizedKeyCmd.Flags().StringVarP(&username, "username", "u", "", "username (required)")
	addAuthorizedKeyCmd.Flags().StringVarP(&keyFile, "key-file", "F", "", "authorized key file to add to VM (required)")
	addAuthorizedKeyCmd.MarkFlagRequired("F")
	addAuthorizedKeyCmd.MarkFlagRequired("u")
}
