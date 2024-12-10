package model

import (
	"context"
	"fmt"
	"strings"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/config"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/templates"
)

type KubeVirtualMachine struct {
	*VirtualMachineV2
	Api *proxmox.Client
}

func (vm *KubeVirtualMachine) EnsureContainerdConfig(ctx context.Context) error {
	pid, _ := vm.AgentExec(ctx, []string{"mkdir", "-p", "/etc/containerd"}, "")
	status, err := vm.WaitForAgentExecExit(ctx, pid, 5)
	if err != nil {
		return err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	vm.AgentFileWrite(ctx, constants.ContainerdConfigPath, templates.ContainerdConfig)
	return nil
}

func (vm *KubeVirtualMachine) RestartContainerd(ctx context.Context) error {
	pid, _ := vm.AgentExec(ctx, []string{"systemctl", "restart", "containerd"}, "")
	status, err := vm.WaitForAgentExecExit(ctx, pid, 10)
	if err != nil {
		return err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	return nil
}

func (vm *KubeVirtualMachine) CreateWorkerJoinCommand(ctx context.Context) ([]string, error) {
	pid, _ := vm.AgentExec(ctx, []string{"kubeadm", "token", "create", "--print-join-command"}, "")
	status, err := vm.WaitForAgentExecExit(ctx, pid, 5)
	if err != nil {
		return nil, err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	cmd := strings.Split(strings.Trim(status.OutData, " \n"), " ")
	return cmd, nil
}

func (vm *KubeVirtualMachine) CreateControlPlaneJoinCommand(ctx context.Context) ([]string, error) {
	pid, _ := vm.AgentExec(ctx, []string{"kubeadm", "token", "create", "--print-join-command"}, "")
	status, err := vm.WaitForAgentExecExit(ctx, pid, 5)
	if err != nil {
		return nil, err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	cmd := append(strings.Split(strings.Trim(status.OutData, " \n"), " "), "--control-plane")
	return cmd, nil
}

func (vm *KubeVirtualMachine) DrainNode(ctx context.Context, nodeName string) (*proxmox.AgentExecStatus, error) {
	cmd := append([]string{"kubectl", fmt.Sprintf("--kubeconfig=%s", constants.KubeadminConfigPath), "drain", nodeName}, config.DrainOpts...)
	pid, _ := vm.AgentExec(ctx, cmd, "")
	status, err := vm.WaitForAgentExecExit(ctx, pid, 30*60) // TODO: configurable
	if err != nil {
		return nil, err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	return status, nil
}

func (vm *KubeVirtualMachine) DeleteNode(ctx context.Context, nodeName string) (*proxmox.AgentExecStatus, error) {
	cmd := []string{"kubectl", fmt.Sprintf("--kubeconfig=%s", constants.KubeadminConfigPath), "delete", "node", nodeName}
	pid, _ := vm.AgentExec(ctx, cmd, "")
	status, err := vm.WaitForAgentExecExit(ctx, pid, 60) // TODO: configurable
	if err != nil {
		return nil, err
	}
	if status.ExitCode != 0 {
		// TODO
	}
	return status, nil
}
