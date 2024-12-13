package model

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"time"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/payload"
)

type VirtualMachineV2 struct {
	*proxmox.VirtualMachine
	ProxmoxClient *proxmox.Client
}

func (vm *VirtualMachineV2) WaitForCloudInit(ctx context.Context) error {
	const errorBudget = 10
	var errorCount = 0
	doneMatcher, _ := regexp.Compile("status: done")
	errorMatcher, _ := regexp.Compile("status: error")
	for errorCount < errorBudget {
		time.Sleep(5 * time.Second)
		pid, err := vm.AgentExec(ctx, constants.CloudInitStatusCmd, "")
		fmt.Println("exec 'cloud-init status'", "pid", pid)
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
		fmt.Printf("exec 'cloud-init status' return: {'stdout':'%s','stderr':'%s'", status.OutData, status.ErrData)
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

func (vm *VirtualMachineV2) AgentFileWrite(ctx context.Context, location string, content string) error {
	err := vm.ProxmoxClient.Post(ctx, fmt.Sprintf("/nodes/%s/qemu/%d/agent/file-write", vm.Node, vm.VMID), map[string]string{"file": location, "content": content}, nil)
	return err
}

func (vm *VirtualMachineV2) AgentFileRead(ctx context.Context, location string, response *payload.AgentFileRead) error {
	err := vm.ProxmoxClient.Get(ctx, fmt.Sprintf("/nodes/%s/qemu/%d/agent/file-read?file=%s", vm.Node, vm.VMID, location), &response)
	if err != nil {
		return err
	}
	return nil
}
