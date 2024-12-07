package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"math"

	"github.com/luthermonson/go-proxmox"
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/templates"
	"github.com/tuana9a/kp/util"
)

var dadId int
var childId int
var vmTemplateId int
var vmNet string
var vmIp string
var vmCores int
var vmMem int
var vmDiskSize string
var vmNamePrefix string
var vmUsername string
var vmPassword string
var vmStartOnBoot bool
var vmUserdata string
var vmSshKeys = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCx5LBYrl0TfkKChabUT6Fdwj40qr1eUCKBxIydmWOscQ+DlptTtN28PMmiIp6WAvYfQAD2lp5F6P1znFqqzKpKL/TFswfjdrbb0Br688jmzbeFAZ8cMDwJAEVxMi9P8Gkl5BxfTcVlrxyPdzfAjWps8DkZ8d8QkdKh6puAqfff1oN5/ubOOnSlvUL89VJmkE4jAuN1P5YTwYuz7mCP33LwBKltUqhLkGw5kKLz9MCF7GQ/9smH/1VKaBAsHMHx93ByISVU8zaVjbNfYE6vyHoDZUkLBZTtgksGZboyp8Rfj4+IBQVZ1xy9MiBQFMEAfNXEAHxD3QWNdRNGfNulqwvxeGNyja32gB+M4Ef4pybQ6KHDqW1aVOCqHLlGsQmMQN6E8HShZKQp9Fkq7kT+9e9LKDoJOem8Hb5E3xPD4umReogccJnHJCNuDQOM+Gfqlj1o4w+RTVA5ss6xsMGqUEdHBgoBYZZ2tgQYrIathq7V9+y0Yy3M4YZyEV9WyQI6HwU= u@tuana9a-dev2"

var createCmd = &cobra.Command{
	Use: "create",
	Run: func(cmd *cobra.Command, args []string) {
		verbose, _ := cmd.Root().PersistentFlags().GetBool("verbose")
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")

		cfg := util.LoadConfig(configPath)
		if verbose {
			fmt.Println("verbose: ", verbose)
		}

		// logger := util.CreateLogger(cfg.LogLevel)
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
			{Name: "balloon", Value: int(math.Max(float64(vmMem/2), 1024))},
			{Name: "vga", Value: "type=qxl"},
			{Name: "agent", Value: "enabled=1"},
			{Name: "ciuser", Value: vmUsername},
			{Name: "cipassword", Value: vmPassword},
			{Name: "net0", Value: fmt.Sprintf("virtio,bridge=%s", vmNet)},
			{Name: "ipconfig0", Value: fmt.Sprintf("ip=%s/%s,gw=%s", vmIp, network.Netmask, gatewayIp)},
			// {Name: "sshkeys", Value: util.EncodeSshKeys(vmSshKeys)},
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

		vmChildV2 := model.VirtualMachineV2{
			V1:     vmChild,
			Client: proxmoxClient,
		}

		fmt.Println("Wait for cloud-init")
		err = vmChildV2.WaitForCloudInit(ctx)
		if err != nil {
			fmt.Println("Error when wait for cloud-init", err)
			return
		}

		fmt.Println("Write setup script")
		err = vmChildV2.AgentFileWrite(ctx, constants.SetupScriptPath, templates.WorkderSetupScriptDefault)
		if err != nil {
			fmt.Println("Error when agent file write setup script")
			return
		}

		fmt.Println("Chmod setup script")
		pid, _ := vmChild.AgentExec(ctx, []string{"chmod", "+x", constants.SetupScriptPath}, "")
		status, _ := vmChild.WaitForAgentExecExit(ctx, pid, 5)
		fmt.Println("Chmod setup script status", status)

		fmt.Println("Exec setup script")
		pid, _ = vmChild.AgentExec(ctx, []string{constants.SetupScriptPath}, "")
		status, _ = vmChild.WaitForAgentExecExit(ctx, pid, 30*60)
		fmt.Println("Exec setup script status", status)

		fmt.Println("write containerd config")
		vmChildV2.EnsureContainerdConfig(ctx)

		fmt.Println("Restart containerd")
		vmChildV2.RestartContainerd(ctx)

		vmDad, err := pveNode.VirtualMachine(ctx, dadId)
		if err != nil {
			fmt.Println("Error when getting vm", dadId, err)
			return
		}
		vmDadV2 := model.VirtualMachineV2{
			V1:     vmDad,
			Client: proxmoxClient,
		}

		fmt.Println("Create join command")
		joinCmd, err := vmDadV2.CreateWorkerJoinCommand(ctx)
		fmt.Println(json.Marshal(joinCmd))
		if err != nil {
			// TODO
		}

		fmt.Println("Exec join command")
		pid, err = vmChild.AgentExec(ctx, joinCmd, "")
		if err != nil {
			// TODO
		}
		status, err = vmChild.WaitForAgentExecExit(ctx, pid, 10*60)
		fmt.Println("Exec join command status", status)
		if err != nil {
			// TODO
		}
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

	createCmd.Flags().IntVar(&vmCores, "vm-cores", 4, "number of VM cores (default: 4)")

	createCmd.Flags().IntVar(&vmMem, "vm-mem", 8192, "amount of VM memory in MB (default: 8192)")

	createCmd.Flags().StringVar(&vmDiskSize, "vm-disk", "+32G", "size of the VM disk (default: +32G)")

	createCmd.Flags().StringVar(&vmNamePrefix, "vm-name-prefix", "i-", "prefix for VM names (default: i-)")

	createCmd.Flags().StringVar(&vmUsername, "vm-username", "u", "username for VM access (default: u)")

	createCmd.Flags().StringVar(&vmPassword, "vm-password", "p", "password for VM access (default: p)")

	createCmd.Flags().BoolVar(&vmStartOnBoot, "vm-start-on-boot", true, "start VM on boot (default: true)")

	createCmd.Flags().StringVar(&vmUserdata, "vm-userdata", "", "user data script for the VM (optional)")
}
