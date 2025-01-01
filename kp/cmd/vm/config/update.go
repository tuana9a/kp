package config

import (
	"context"
	"fmt"
	"math"

	"github.com/luthermonson/go-proxmox"
	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/kp/util"
)

var updateCmd = &cobra.Command{
	Use: "update",
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

		newConfig := []proxmox.VirtualMachineOption{}

		if vmName := fmt.Sprintf("%s%d", vmNamePrefix, vmid); vmName != "" {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "name", Value: vmName})
		}
		if cpu := "cputype=host"; cpu != "" {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "cpu", Value: cpu})
		}
		if vmCores != 0 {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "cores", Value: vmCores})
		}
		if vmMem != 0 {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "memory", Value: vmMem})
		}
		if vmMemBallooned {
			balloon := int(math.Min(math.Max(float64(vmMem/2), 1024), float64(vmMem)))
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "balloon", Value: balloon})
		}
		if vga := "type=qxl"; vga != "" {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "vga", Value: vga})
		}
		if agent := "enabled=1"; agent != "" {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "agent", Value: agent})
		}
		if vmUsername != "" {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "ciuser", Value: vmUsername})
		}
		if vmPassword != "" {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "cipassword", Value: vmPassword})
		}
		if vmNet != "" {
			net0 := fmt.Sprintf("virtio,bridge=%s", vmNet)
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "net0", Value: net0})

			ipconfig0 := fmt.Sprintf("ip=%s,gw=%s", vmIp, vmGatewayIp)
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "ipconfig0", Value: ipconfig0})
		}
		if vmStartOnBoot {
			newConfig = append(newConfig, proxmox.VirtualMachineOption{Name: "onboot", Value: vmStartOnBoot})
		}
		fmt.Println("vm update_config", vmid, newConfig)
		task, err := vm.Config(ctx, newConfig...)
		if err != nil {
			fmt.Println("ERROR vm update_config", err)
			return
		}
		_, completed, _ := task.WaitForCompleteStatus(ctx, 30)
		fmt.Println("Wait for update config task", "completed", completed)
		if !completed {
			fmt.Println("Can not update vm config", "taskId", task.ID)
			return
		}
	},
}

func init() {
	updateCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	updateCmd.Flags().StringVar(&vmNet, "vm-net", "", "VM network (required)")
	updateCmd.Flags().StringVar(&vmIp, "vm-ip", "", "ex: 192.168.56.22/24 (required)")
	updateCmd.Flags().StringVar(&vmGatewayIp, "vm-gateway-ip", "", "VM network gateway ip(required)")
	updateCmd.MarkFlagsRequiredTogether("vm-net", "vm-ip", "vm-gateway-ip")
	updateCmd.Flags().StringVar(&vmNamePrefix, "vm-name-prefix", "i-", "prefix for VM names (default: i-)")
	updateCmd.Flags().IntVar(&vmCores, "vm-cores", 0, "number of VM cores (default: 2)")
	updateCmd.Flags().IntVar(&vmMem, "vm-mem", 0, "amount of VM memory in MB (default: 4096)")
	updateCmd.Flags().BoolVar(&vmMemBallooned, "vm-mem-balloon", false, "")
	updateCmd.Flags().StringVar(&vmUsername, "vm-username", "u", "username for VM access (default: u)")
	updateCmd.Flags().StringVar(&vmPassword, "vm-password", "p", "password for VM access (default: p)")
	updateCmd.Flags().BoolVar(&vmStartOnBoot, "vm-start-on-boot", false, "start VM on boot (default: false)")
}
