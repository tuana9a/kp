package apiserver

import (
	"context"
	"encoding/json"
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/tuana9a/kp/constants"
	"github.com/tuana9a/kp/model"
	"github.com/tuana9a/kp/payload"
	"github.com/tuana9a/kp/util"
	"sigs.k8s.io/yaml"

	v1 "k8s.io/api/core/v1"
)

var vmid int
var addFlagsFile string

var ApiServerCmd = &cobra.Command{
	Use: "apiserver",
}

type AddFlagsInput struct {
	Flags []string `json:"flags"`
}

type ApiserverFlag struct {
	Value   string
	Existed bool
}

var addFlagsCmd = &cobra.Command{
	Use: "add-flags",
	Run: func(cmd *cobra.Command, args []string) {
		configPath, _ := cmd.Root().PersistentFlags().GetString("config")
		cfg := util.LoadConfig(configPath)

		blob, err := os.ReadFile(addFlagsFile)
		if err != nil {
			panic(err)
		}
		var addFlagInput AddFlagsInput
		json.Unmarshal(blob, &addFlagInput)
		flagCount := len(addFlagInput.Flags)
		flags := make([]ApiserverFlag, flagCount)
		for i, flag := range addFlagInput.Flags {
			flags[i].Value = flag
		}

		proxmoxClient, _ := util.CreateProxmoxClient(cfg)
		version, err := proxmoxClient.Version(context.Background())
		if err != nil {
			panic(err)
		}
		fmt.Println("proxmox-api version: ", version.Version)
		ctx := context.Background()

		pveNode, err := proxmoxClient.Node(ctx, cfg.ProxmoxNode)
		if err != nil {
			panic(err)
		}

		vm, err := pveNode.VirtualMachine(ctx, vmid)
		if err != nil {
			panic(err)
		}

		kubeVm := &model.KubeVirtualMachine{
			VirtualMachineV2: &model.VirtualMachineV2{
				VirtualMachine: vm,
				ProxmoxClient:  proxmoxClient,
			},
		}
		var kubeApiServerYamlContent string
		var agentReadFileResponse payload.AgentFileRead
		var kubeApiServerPod v1.Pod
		err = kubeVm.AgentFileRead(ctx, constants.KubeApiServerYamlPath, &agentReadFileResponse)
		if err != nil {
			panic(err)
		}
		if agentReadFileResponse.Truncated {
			// TODO
			fmt.Println("WARN file read truncated")
		}
		kubeApiServerYamlContent = agentReadFileResponse.Content
		fmt.Println(kubeApiServerYamlContent)
		err = yaml.Unmarshal([]byte(kubeApiServerYamlContent), &kubeApiServerPod)
		if err != nil {
			panic(err)
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
			fmt.Println(flags[i].Existed, flags[i].Value)
			if !flags[i].Existed {
				containerCommand = append(containerCommand, flags[i].Value)
			}
		}
		kubeApiServerPod.Spec.Containers[0].Command = containerCommand
		blob, err = yaml.Marshal(kubeApiServerPod)
		if err != nil {
			panic(err)
		}

		err = kubeVm.AgentFileWrite(ctx, constants.KubeApiServerYamlPath, string(blob))
		if err != nil {
			panic(err)
		}
	},
}

func init() {
	addFlagsCmd.Flags().IntVar(&vmid, "vmid", 0, "vmid (required)")
	addFlagsCmd.MarkFlagRequired("vmid")
	addFlagsCmd.Flags().StringVar(&addFlagsFile, "file", "", "file (required)")
	addFlagsCmd.MarkFlagRequired("file")
	ApiServerCmd.AddCommand(addFlagsCmd)
}
