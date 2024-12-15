package vm

import (
	"context"
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/model"
	"github.com/tuana9a/kp/kp/util"
)

var injectAuthorizedKeysCmd = &cobra.Command{
	Use: "inject-authorized-keys",
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

		pid, _ := vmV2.AgentExec(ctx, []string{"mkdir", "-p", fmt.Sprintf("/home/%s/.ssh", vmUsername)}, "")
		status, _ := vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("mkdir ~/.ssh status", status)

		pid, _ = vmV2.AgentExec(ctx, []string{"chown", "-R", fmt.Sprintf("%s:%s", vmUsername, vmUsername), fmt.Sprintf("/home/%s/.ssh", vmUsername)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("chown ~/.ssh status", status)

		pid, _ = vmV2.AgentExec(ctx, []string{"chmod", "-R", "700", fmt.Sprintf("/home/%s/.ssh", vmUsername)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("chmod ~/.ssh status", status)

		fmt.Println("write ~/.ssh/authorized_keys")
		blob, err := os.ReadFile(vmAuthoriedKeysFile)
		if err != nil {
			fmt.Println("Error when reading vmAuthoriedKeysFile", err)
			return
		}
		err = vmV2.AgentFileWrite(ctx, fmt.Sprintf("/home/%s/.ssh/authorized_keys", vmUsername), string(blob))
		if err != nil {
			fmt.Println("Error when writing ~/.ssh/authorized_keys", err)
			return
		}

		fmt.Println("chmod ~/.ssh/authorized_keys")
		pid, _ = vmV2.AgentExec(ctx, []string{"chmod", "700", fmt.Sprintf("/home/%s/.ssh/authorized_keys", vmUsername)}, "")
		status, _ = vmV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("chmod ~/.ssh/authorized_keys status", status)
	},
}

func init() {
	injectAuthorizedKeysCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	injectAuthorizedKeysCmd.MarkFlagRequired("vmid")
	injectAuthorizedKeysCmd.Flags().StringVar(&vmAuthoriedKeysFile, "vm-authorized-keys-file", fmt.Sprintf("%s/.ssh/id_rsa.pub", os.Getenv("HOME")), "authorized keys file to write to VM (default: ~/.ssh/id_rsa.pub)")
}
