package model

import (
	"context"
	"fmt"
	"strings"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/templates"
)

type VirtualMachineV2 struct {
	V1     *proxmox.VirtualMachine
	Client *proxmox.Client
}

func (vm *VirtualMachineV2) AgentFileWrite(ctx context.Context, location string, content string) error {
	err := vm.Client.Post(ctx, fmt.Sprintf("/nodes/%s/qemu/%d/agent/file-write", vm.V1.Node, vm.V1.VMID), map[string]string{"file": location, "content": content}, nil)
	return err
}

func (vm *VirtualMachineV2) AgentFileRead(ctx context.Context, location string, content *string) error {
	err := vm.Client.Get(ctx, fmt.Sprintf("/nodes/%s/qemu/%d/agent/file-read?file=%s", vm.V1.Node, vm.V1.VMID, location), &content)
	return err
}

func (vm *VirtualMachineV2) EnsureContainerdConfig(ctx context.Context) error {
	pid, _ := vm.V1.AgentExec(ctx, []string{"mkdir", "-p", "/etc/containerd"}, "")
	status, err := vm.V1.WaitForAgentExecExit(ctx, pid, 5)
	if err != nil {
		return err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	vm.AgentFileWrite(ctx, constants.ContainerdConfigPath, templates.ContainerdConfig)
	return nil
}

func (vm *VirtualMachineV2) RestartContainerd(ctx context.Context) error {
	pid, _ := vm.V1.AgentExec(ctx, []string{"systemctl", "restart", "containerd"}, "")
	status, err := vm.V1.WaitForAgentExecExit(ctx, pid, 10)
	if err != nil {
		return err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	return nil
}

func (vm *VirtualMachineV2) CreateWorkerJoinCommand(ctx context.Context) ([]string, error) {
	pid, _ := vm.V1.AgentExec(ctx, []string{"kubeadm", "token", "create", "--print-join-command"}, "")
	status, err := vm.V1.WaitForAgentExecExit(ctx, pid, 5)
	if err != nil {
		return nil, err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	cmd := strings.Split(strings.Trim(status.OutData, " \n"), " ")
	return cmd, nil
}

func (vm *VirtualMachineV2) CreateControlPlaneJoinCommand(ctx context.Context) ([]string, error) {
	pid, _ := vm.V1.AgentExec(ctx, []string{"kubeadm", "token", "create", "--print-join-command"}, "")
	status, err := vm.V1.WaitForAgentExecExit(ctx, pid, 5)
	if err != nil {
		return nil, err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	cmd := append(strings.Split(strings.Trim(status.OutData, " \n"), " "), "--control-plane")
	return cmd, nil
}

func (vm *VirtualMachineV2) WaitForCloudInit(ctx context.Context) error {
	pid, _ := vm.V1.AgentExec(ctx, constants.CloudInitWaitCmd, "")
	fmt.Println("Wait for cloud-init", "pid", pid)
	status, err := vm.V1.WaitForAgentExecExit(ctx, pid, 15*60)
	if err != nil {
		// 500 Agent error: Invalid parameter 'pid'
		fmt.Println("Wait for cloud-init has error", err)
		// But we can continue
		return nil
	}
	if status.ExitCode != 0 {
		fmt.Println("Wait for cloud init did not exit successfully")
		fmt.Println("stdout")
		fmt.Println(status.OutData)
		fmt.Println("stderr")
		fmt.Println(status.ErrData)
	}
	return nil
}
