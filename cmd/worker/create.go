package worker

import (
	"context"
	"fmt"
	"time"

	"github.com/luthermonson/go-proxmox"
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/util"
	"go.uber.org/zap"
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
		config, _ := cmd.Root().PersistentFlags().GetString("config")

		cfg := util.LoadConfig(config)
		if verbose {
			fmt.Println("verbose: ", verbose)
		}
		newVmName := vmNamePrefix + string(childId)

		logger := util.CreateLogger(cfg.LogLevel)
		proxmoxClient := util.CreateProxmoxClient(cfg)
		ctx := context.Background()

		node, err := proxmoxClient.Node(ctx, cfg.ProxmoxNode)
		if err != nil {
			logger.Error("Error when getting proxmox node", zap.Error(err))
			return
		}

		network, err := node.Network(ctx, vmNet)
		if err != nil {
			logger.Error("Error when getting node network", zap.Error(err))
			return
		}

		logger.Debug("network", zap.String("name", vmNet), zap.String("gateway", network.Gateway))
		gatewayIp := network.Gateway
		vmTemplate, err := node.VirtualMachine(ctx, vmTemplateId)
		if err != nil {
			logger.Error("Error when getting vm", zap.Error(err))
			return
		}

		_, cloneTask, err := vmTemplate.Clone(ctx, &proxmox.VirtualMachineCloneOptions{
			NewID: childId,
		})
		if err != nil {
			logger.Error("Error when cloning vm", zap.Error(err))
			return
		}

		cloneStatus, isCloneCompleted, _ := cloneTask.WaitForCompleteStatus(ctx, 30)
		logger.Debug("Wait for clone task", zap.Bool("status", cloneStatus), zap.Bool("completed", isCloneCompleted))
		if !isCloneCompleted {
			logger.Error("Can not complete cloning vm", zap.String("taskId", cloneTask.ID))
			return
		}

		vmChild, err := node.VirtualMachine(ctx, childId)
		if err != nil {
			logger.Error("Error when getting vm", zap.Error(err))
			return
		}

		updateConfigTask, err := vmChild.Config(ctx,
			proxmox.VirtualMachineOption{Name: "name", Value: newVmName},
			proxmox.VirtualMachineOption{Name: "cpu", Value: "cputype=host"},
			proxmox.VirtualMachineOption{Name: "cores", Value: vmCores},
			proxmox.VirtualMachineOption{Name: "memory", Value: vmMem},
			proxmox.VirtualMachineOption{Name: "agent", Value: "enabled=1"},
			proxmox.VirtualMachineOption{Name: "ciuser", Value: vmUsername},
			proxmox.VirtualMachineOption{Name: "cipassword", Value: vmPassword},
			proxmox.VirtualMachineOption{Name: "net0", Value: fmt.Sprintf("virtio,bridge=%s", vmNet)},
			proxmox.VirtualMachineOption{Name: "ipconfig0", Value: fmt.Sprintf("ip=%s/%s,gw=%s", vmNet, network.Netmask, gatewayIp)},
			proxmox.VirtualMachineOption{Name: "sshkeys", Value: vmSshKeys},
			proxmox.VirtualMachineOption{Name: "onboot", Value: vmStartOnBoot},
		)
		if err != nil {
			logger.Error("Error when update vm config", zap.Error(err))
			return
		}
		updateConfigStatus, isUpdateConfigCompleted, _ := updateConfigTask.WaitForCompleteStatus(ctx, 30)
		logger.Debug("Wait for update config task", zap.Bool("status", updateConfigStatus), zap.Bool("completed", isUpdateConfigCompleted))
		if !isUpdateConfigCompleted {
			logger.Error("Can not update vm config", zap.String("taskId", updateConfigTask.ID))
			return
		}

		err = vmChild.ResizeDisk(ctx, "scsi0", vmDiskSize)
		if err != nil {
			logger.Error("Error when resize disk vm", zap.Error(err))
			return
		}

		startVmTask, _ := vmChild.Start(ctx)
		startVmTask.WaitForCompleteStatus(ctx, 60)
		vmChild.WaitForAgent(ctx, 5*60)
		vmChild.WaitForAgentExecExit()
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

	createCmd.Flags().StringVar(&vmPassword, "vm-password", fmt.Sprintf("%d", time.Now().UnixNano()), "password for VM access (default: current timestamp)")

	createCmd.Flags().BoolVar(&vmStartOnBoot, "vm-start-on-boot", true, "start VM on boot (default: true)")

	createCmd.Flags().StringVar(&vmUserdata, "vm-userdata", "", "user data script for the VM (optional)")
}
