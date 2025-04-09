package apiserver

import (
	"context"
	"encoding/json"
	"os"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/payload"
	"github.com/tuana9a/kp/util"
	v1 "k8s.io/api/core/v1"
	"sigs.k8s.io/yaml"
)

var addFlagsCmd = &cobra.Command{
	Use: "add-flags",
	Run: func(cmd *cobra.Command, args []string) {
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		util.Sugar().Infof("configPath: %s", configPath)
		cfg := util.LoadConfig(configPath)

		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		version, err := proxmoxClient.Version(context.Background())
		if err != nil {
			util.Sugar().Errorf("test proxmox connection error", err)
			return
		}
		util.Sugar().Info("proxmox-api version: %s", version.Version)
		ctx := context.Background()

		pveNode, err := proxmoxClient.Node(ctx, cfg.ProxmoxNode)
		if err != nil {
			util.Sugar().Info("get proxmox node error: %s", err)
			return
		}

		vm, err := pveNode.VirtualMachine(ctx, vmid)
		if err != nil {
			util.Sugar().Info("get vm error: %s", err)
			return
		}

		kubeVm := &model.KubeVirtualMachine{
			VirtualMachineV2: &model.VirtualMachineV2{
				VirtualMachine: vm,
				ProxmoxClient:  proxmoxClient,
			},
		}

		blob, err := os.ReadFile(flagsFile)
		if err != nil {
			util.Sugar().Errorf("read flag file error %s", flagsFile, err)
			return
		}
		var addFlagInput payload.AddFlagsInput
		json.Unmarshal(blob, &addFlagInput)
		flagCount := len(addFlagInput.Flags)
		flags := make([]payload.ApiserverFlag, flagCount)
		for i, flag := range addFlagInput.Flags {
			flags[i].Value = flag
		}

		var kubeApiServerYamlContent string
		var agentReadFileResponse payload.AgentFileRead
		var kubeApiServerPod v1.Pod
		err = kubeVm.AgentFileRead(ctx, constants.KubeApiServerYamlPath, &agentReadFileResponse)
		if err != nil {
			util.Sugar().Errorf("agent read file error: %s", err)
			return
		}
		if agentReadFileResponse.Truncated {
			// TODO
			util.Sugar().Infof("WARN file read truncated")
		}
		kubeApiServerYamlContent = agentReadFileResponse.Content
		util.Sugar().Infof("kubeApiServerYamlContent", kubeApiServerYamlContent)
		err = yaml.Unmarshal([]byte(kubeApiServerYamlContent), &kubeApiServerPod)
		if err != nil {
			util.Sugar().Errorf("yaml unmarshal error: %s", err)
		}
		var containerCommand = kubeApiServerPod.Spec.Containers[0].Command
		for i := 0; i < len(containerCommand); i++ {
			for j := 0; j < flagCount; j++ {
				if containerCommand[i] == flags[j].Value {
					flags[j].Existed = true
				}
			}
		}
		for i := 0; i < flagCount; i++ {
			util.Sugar().Infof("existed %s value %s", flags[i].Existed, flags[i].Value)
			if !flags[i].Existed {
				containerCommand = append(containerCommand, flags[i].Value)
			}
		}
		kubeApiServerPod.Spec.Containers[0].Command = containerCommand
		blob, err = yaml.Marshal(kubeApiServerPod)
		if err != nil {
			util.Sugar().Errorf("yarml marshal %s", err)
		}

		err = kubeVm.AgentFileWrite(ctx, constants.KubeApiServerYamlPath, string(blob))
		if err != nil {
			util.Sugar().Errorf("agent write file %s", err)
		}
	},
}

func init() {
	addFlagsCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	addFlagsCmd.MarkFlagRequired("vmid")
	addFlagsCmd.Flags().StringVar(&flagsFile, "file", "", "file (required)")
	addFlagsCmd.MarkFlagRequired("file")
	ApiServerCmd.AddCommand(addFlagsCmd)
}
