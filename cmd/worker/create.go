package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"os"

	"github.com/luthermonson/go-proxmox"
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/templates"
	"github.com/tuana9a/kp/util"
)

var createCmd = &cobra.Command{
	Use: "create",
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

		vmTemplate, err := pveNode.VirtualMachine(ctx, vmTemplateId)
		if err != nil {
			fmt.Println("Error when getting template vm", err)
			return
		}

		_, task, err := vmTemplate.Clone(ctx, &proxmox.VirtualMachineCloneOptions{
			NewID: childId,
		})
		if err != nil {
			fmt.Println("Error when cloning vm", err)
			return
		}
		_, completed, _ := task.WaitForCompleteStatus(ctx, 30)
		fmt.Println("Wait for clone task", completed)
		if !completed {
			fmt.Println("Can not complete cloning vm", task.ID)
			return
		}

		vmChild, err := pveNode.VirtualMachine(ctx, childId)
		if err != nil {
			fmt.Println("Error when getting child vm", childId, err)
			return
		}

		err = vmChild.ResizeDisk(ctx, "scsi0", vmDiskSize)
		if err != nil {
			fmt.Println("Error when resize disk child vm", childId, err)
			return
		}

		network, err := pveNode.Network(ctx, vmNet)
		fmt.Println("network", network)
		if err != nil {
			fmt.Println("Error when getting node network", err)
			return
		}

		gatewayIp := network.Address
		fmt.Println("network", vmNet, "gatewayIp", gatewayIp)

		newConfig := []proxmox.VirtualMachineOption{
			{Name: "name", Value: fmt.Sprintf("%s%d", vmNamePrefix, childId)},
			{Name: "cpu", Value: "cputype=host"},
			{Name: "cores", Value: vmCores},
			{Name: "memory", Value: vmMem},
			{Name: "balloon", Value: int(math.Min(math.Max(float64(vmMem/2), 1024), float64(vmMem)))},
			{Name: "vga", Value: "type=qxl"},
			{Name: "agent", Value: "enabled=1"},
			{Name: "ciuser", Value: vmUsername},
			{Name: "cipassword", Value: vmPassword},
			{Name: "net0", Value: fmt.Sprintf("virtio,bridge=%s", vmNet)},
			{Name: "ipconfig0", Value: fmt.Sprintf("ip=%s/%s,gw=%s", vmIp, network.Netmask, gatewayIp)},
			{Name: "onboot", Value: vmStartOnBoot},
		}
		fmt.Println("Update child vm config", childId, newConfig)
		task, err = vmChild.Config(ctx, newConfig...)
		if err != nil {
			fmt.Println("Error when update vm config", err)
			return
		}
		_, completed, _ = task.WaitForCompleteStatus(ctx, 30)
		fmt.Println("Wait for update config task", "completed", completed)
		if !completed {
			fmt.Println("Can not update vm config", "taskId", task.ID)
			return
		}

		fmt.Println("Start vm", childId)
		task, err = vmChild.Start(ctx)
		if err != nil {
			fmt.Println("Failed to start vm")
			return
		}
		task.WaitForCompleteStatus(ctx, 60)

		fmt.Println("Wait for agent")
		err = vmChild.WaitForAgent(ctx, 5*60)
		if err != nil {
			fmt.Println("Error when wait for agent", err)
			return
		}

		vmChildV2 := &model.VirtualMachineV2{
			VirtualMachine: vmChild,
			Api:            proxmoxClient,
		}

		fmt.Println("Wait for cloud-init")
		err = vmChildV2.WaitForCloudInit(ctx)
		if err != nil {
			fmt.Println("Error when wait for cloud-init", err)
			return
		}

		if vmAuthoriedKeysFile != "" {
			pid, _ := vmChildV2.AgentExec(ctx, []string{"mkdir", "-p", fmt.Sprintf("/home/%s/.ssh", vmUsername)}, "")
			status, _ := vmChildV2.WaitForAgentExecExit(ctx, pid, 5)
			fmt.Println("Mkdir ~/.ssh status", status)

			pid, _ = vmChildV2.AgentExec(ctx, []string{"chown", "-R", fmt.Sprintf("%s:%s", vmUsername, vmUsername), fmt.Sprintf("/home/%s/.ssh", vmUsername)}, "")
			status, _ = vmChildV2.WaitForAgentExecExit(ctx, pid, 5)
			fmt.Println("Chown ~/.ssh status", status)

			pid, _ = vmChildV2.AgentExec(ctx, []string{"chmod", "-R", "700", fmt.Sprintf("/home/%s/.ssh", vmUsername)}, "")
			status, _ = vmChildV2.WaitForAgentExecExit(ctx, pid, 5)
			fmt.Println("Chmod ~/.ssh status", status)

			fmt.Println("Write ~/.ssh/authorized_keys")
			blob, err := os.ReadFile(vmAuthoriedKeysFile)
			if err != nil {
				fmt.Println("Error when reading vmAuthoriedKeysFile", err)
				return
			}
			err = vmChildV2.AgentFileWrite(ctx, fmt.Sprintf("/home/%s/.ssh/authorized_keys", vmUsername), string(blob))
			if err != nil {
				fmt.Println("Error when writing ~/.ssh/authorized_keys", err)
				return
			}

			fmt.Println("Chmod ~/.ssh/authorized_keys")
			pid, _ = vmChildV2.AgentExec(ctx, []string{"chmod", "700", fmt.Sprintf("/home/%s/.ssh/authorized_keys", vmUsername)}, "")
			status, _ = vmChildV2.WaitForAgentExecExit(ctx, pid, 5)
			fmt.Println("Chmod ~/.ssh/authorized_keys status", status)
		}

		fmt.Println("Write setup script")
		err = vmChildV2.AgentFileWrite(ctx, constants.SetupScriptPath, templates.WorkderSetupScriptDefault)
		if err != nil {
			fmt.Println("Error when agent file write setup script")
			return
		}

		fmt.Println("Chmod setup script")
		pid, _ := vmChild.AgentExec(ctx, []string{"chmod", "+x", constants.SetupScriptPath}, "")
		status, _ := vmChildV2.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("Chmod setup script status", status)

		fmt.Println("Exec setup script")
		pid, _ = vmChild.AgentExec(ctx, []string{constants.SetupScriptPath}, "")
		status, _ = vmChildV2.WaitForAgentExecExit(ctx, pid, 30*60)
		fmt.Println("Exec setup script status", status)

		if vmUserdata != "" {
			content, err := os.ReadFile(vmUserdata)
			if err != nil {
				fmt.Println("Error reading userdata file", vmUserdata)
				return
			}
			fmt.Println("Write userdata script")
			err = vmChildV2.AgentFileWrite(ctx, constants.UserdataScriptPath, string(content))
			if err != nil {
				fmt.Println("Error when agent file write userdata script")
				return
			}

			fmt.Println("Chmod userdata script")
			pid, _ := vmChild.AgentExec(ctx, []string{"chmod", "+x", constants.UserdataScriptPath}, "")
			status, _ := vmChildV2.WaitForAgentExecExit(ctx, pid, 5)
			fmt.Println("Chmod userdata script status", status)

			fmt.Println("Exec userdata script")
			pid, _ = vmChild.AgentExec(ctx, []string{constants.UserdataScriptPath}, "")
			status, _ = vmChildV2.WaitForAgentExecExit(ctx, pid, 30*60)
			fmt.Println("Exec userdata script status", status)
		}

		kubeVmChild := &model.KubeVirtualMachine{
			VirtualMachineV2: vmChildV2,
			Api:              proxmoxClient,
		}
		fmt.Println("write containerd config")
		kubeVmChild.EnsureContainerdConfig(ctx)

		fmt.Println("Restart containerd")
		kubeVmChild.RestartContainerd(ctx)

		vmDad, err := pveNode.VirtualMachine(ctx, dadId)
		if err != nil {
			fmt.Println("Error when getting vm", dadId, err)
			return
		}
		vmDadV2 := &model.VirtualMachineV2{
			VirtualMachine: vmDad,
			Api:            proxmoxClient,
		}
		kubeVmDad := model.KubeVirtualMachine{
			VirtualMachineV2: vmDadV2,
			Api:              proxmoxClient,
		}

		fmt.Println("Create join command")
		joinCmd, err := kubeVmDad.CreateWorkerJoinCommand(ctx)
		fmt.Println(json.Marshal(joinCmd))
		if err != nil {
			// TODO
		}

		fmt.Println("Exec join command")
		pid, err = vmChild.AgentExec(ctx, joinCmd, "")
		if err != nil {
			// TODO
		}
		status, err = vmChildV2.WaitForAgentExecExit(ctx, pid, 10*60)
		if err != nil {
			// TODO
			fmt.Println("Error when exec join command", err)
			return
		}
		fmt.Println("Exec join command status", status)
		if status.ExitCode != 0 {
			// TODO
		}
	},
}

func init() {
	createCmd.Flags().IntVar(&dadId, "dad-id", 0, "dad id or control plane id (required)")
	createCmd.MarkFlagRequired("dad-id")

	createCmd.Flags().IntVar(&childId, "child-id", 0, "child id or node id (required)")
	createCmd.MarkFlagRequired("child-id")

	createCmd.Flags().IntVar(&vmTemplateId, "vm-template-id", 0, "template id (required)")
	createCmd.MarkFlagRequired("vm-template-id")

	createCmd.Flags().StringVar(&vmNet, "vm-net", "", "VM network (required)")
	createCmd.MarkFlagRequired("vm-net")

	createCmd.Flags().StringVar(&vmIp, "vm-ip", "", "VM IP address (required)")
	createCmd.MarkFlagRequired("vm-ip")

	createCmd.Flags().StringVar(&vmNamePrefix, "vm-name-prefix", "i-", "prefix for VM names (default: i-)")
	createCmd.Flags().IntVar(&vmCores, "vm-cores", 4, "number of VM cores (default: 4)")
	createCmd.Flags().IntVar(&vmMem, "vm-mem", 8192, "amount of VM memory in MB (default: 8192)")
	createCmd.Flags().StringVar(&vmDiskSize, "vm-disk", "+30G", "size of the VM disk (default: +30G)")
	createCmd.Flags().StringVar(&vmUsername, "vm-username", "u", "username for VM access (default: u)")
	createCmd.Flags().StringVar(&vmPassword, "vm-password", "p", "password for VM access (default: p)")
	createCmd.Flags().StringVar(&vmAuthoriedKeysFile, "vm-authorized-keys-file", fmt.Sprintf("%s/.ssh/id_rsa.pub", os.Getenv("HOME")), "authorized keys file to write to VM (default: ~/.ssh/id_rsa.pub)")
	createCmd.Flags().StringVar(&vmUserdata, "vm-userdata", "", "user data script for the VM (optional)")
	createCmd.Flags().BoolVar(&vmStartOnBoot, "vm-start-on-boot", true, "start VM on boot (default: true)")
}
