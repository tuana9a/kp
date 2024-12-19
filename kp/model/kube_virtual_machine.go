package model

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"text/template"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/kp/config"
	"github.com/tuana9a/kp/kp/constants"
	"github.com/tuana9a/kp/kp/payload"
	"github.com/tuana9a/kp/kp/templates"
)

type KubeVirtualMachine struct {
	*VirtualMachineV2
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

func (vm *KubeVirtualMachine) EnsureCertDirs(ctx context.Context) error {
	pid, err := vm.AgentExec(ctx, append([]string{"mkdir", "-p"}, constants.KubeCertDirs...), "")
	if err != nil {
		return err
	}
	status, err := vm.WaitForAgentExecExit(ctx, pid, 10)
	if err != nil {
		return err
	}
	fmt.Println(status.ExitCode)
	return nil
}

func (vm *KubeVirtualMachine) CopyKubeCerts(ctx context.Context, childVm *KubeVirtualMachine) {
	for _, filepath := range constants.KubeCertPaths {
		vm.CopyFileToVm(ctx, childVm, filepath)
	}
}

func (vm *KubeVirtualMachine) InstallKubevip(ctx context.Context, inf string, vip string) error {
	tmpl, err := template.New("kubevip").Parse(templates.KubevipTemplate)
	if err != nil {
		return err
	}
	var output bytes.Buffer
	err = tmpl.Execute(&output, payload.InstallKubevip{Inf: inf, VIP: vip})
	if err != nil {
		fmt.Println("Error", err)
		return err
	}
	content := output.String()
	vm.AgentFileWrite(ctx, constants.KubevipYamlPath, content)
	return nil
}

func (vm *KubeVirtualMachine) KubeadmReset(ctx context.Context) error {
	pid, err := vm.AgentExec(ctx, []string{"kubeadm", "reset", "-f"}, "")
	if err != nil {
		return err
	}
	status, err := vm.WaitForAgentExecExit(ctx, pid, 15*60)
	if err != nil {
		return err
	}
	fmt.Println(status.OutData)
	fmt.Println(status.ErrData)
	return nil
}

func (vm *KubeVirtualMachine) ListEtcdMembers(ctx context.Context) (*payload.EtcdMemberListOut, error) {
	opts := []string{"--cacert=/etc/kubernetes/pki/etcd/ca.crt",
		"--cert=/etc/kubernetes/pki/apiserver-etcd-client.crt",
		"--key=/etc/kubernetes/pki/apiserver-etcd-client.key"}
	pid, err := vm.AgentExec(ctx, append([]string{"/usr/local/bin/etcdctl", "member", "list", "-w", "json"}, opts...), "")
	if err != nil {
		return nil, err
	}
	status, err := vm.WaitForAgentExecExit(ctx, pid, 60)
	if err != nil {
		return nil, err
	}
	fmt.Println(status.OutData)
	fmt.Println(status.ErrData)
	var out *payload.EtcdMemberListOut
	err = json.Unmarshal([]byte(status.OutData), out)
	if err != nil {
		return nil, err
	}
	return out, nil
}
