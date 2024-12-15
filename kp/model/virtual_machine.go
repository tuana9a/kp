package model

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"time"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/kp/constants"
	"github.com/tuana9a/kp/kp/payload"
)

type IVirtualMachineV2 interface {
	AgentFileWrite(ctx context.Context, location string, content string) error
	AgentFileRead(ctx context.Context, location string, response *payload.AgentFileRead) error
}

type VirtualMachineV2 struct {
	*proxmox.VirtualMachine
	ProxmoxClient *proxmox.Client
}

func CreateVirtualMachineV2(v1 *proxmox.VirtualMachine, client proxmox.Client) *VirtualMachineV2 {
	return &VirtualMachineV2{
		VirtualMachine: v1,
		ProxmoxClient:  &client,
	}
}

func (vm *VirtualMachineV2) WaitForCloudInit(ctx context.Context) error {
	const errorBudget = 10
	var errorCount = 0
	doneMatcher, _ := regexp.Compile("status: done")
	errorMatcher, _ := regexp.Compile("status: error")
	for errorCount < errorBudget {
		time.Sleep(5 * time.Second)
		pid, err := vm.AgentExec(ctx, constants.CloudInitStatusCmd, "")
		if err != nil {
			fmt.Println("exec 'cloud-init status'", "pid", pid, "err", err)
			errorCount += 1
			continue
		}
		status, err := vm.WaitForAgentExecExit(ctx, pid, 10)
		if err != nil {
			fmt.Println("wait for 'cloud-init status'", "pid", pid, "err", err)
			errorCount += 1
			continue
		}
		fmt.Printf("cloud-init status {'pid':%d,'stdout':%d,'stderr':%d}\n", pid, len(status.OutData), len(status.ErrData))
		DONE := doneMatcher.Match([]byte(status.OutData))
		if DONE {
			return nil
		}
		ERROR := errorMatcher.Match([]byte(status.OutData))
		if ERROR {
			return errors.New("'cloud-init status' returns 'status: error'")
		}
	}
	return fmt.Errorf("'cloud-init status' exceed error budget %d of %d", errorCount, errorBudget)
}

func (vm *VirtualMachineV2) AgentFileWrite(ctx context.Context, filepath string, content string) error {
	err := vm.ProxmoxClient.Post(ctx, fmt.Sprintf("/nodes/%s/qemu/%d/agent/file-write", vm.Node, vm.VMID), map[string]string{"file": filepath, "content": content}, nil)
	return err
}

func (vm *VirtualMachineV2) AgentFileRead(ctx context.Context, filepath string, response *payload.AgentFileRead) error {
	err := vm.ProxmoxClient.Get(ctx, fmt.Sprintf("/nodes/%s/qemu/%d/agent/file-read?file=%s", vm.Node, vm.VMID, filepath), &response)
	if err != nil {
		return err
	}
	return nil
}

func (vm *VirtualMachineV2) CopyFileToVm(ctx context.Context, targetVm IVirtualMachineV2, filepath string) error {
	var response payload.AgentFileRead
	err := vm.AgentFileRead(ctx, filepath, &response)
	if err != nil {
		return err
	}
	if response.Truncated {
		// TODO
	}
	err = targetVm.AgentFileWrite(ctx, filepath, response.Content)
	if err != nil {
		return err
	}
	return nil
}
