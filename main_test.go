package main

import (
	"fmt"
	"os"
	"testing"

	v1 "k8s.io/api/core/v1"
	"sigs.k8s.io/yaml"
)

func TestPodYamlUnmarshal(t *testing.T) {
	blob, err := os.ReadFile("./examples/manifests/kube-apiserver.yaml")
	if err != nil {
		t.Error("os.ReadFile", err)
	}
	var pod v1.Pod
	err = yaml.Unmarshal(blob, &pod)
	if err != nil {
		t.Error("yaml.Unmarshal", err)
	}
	fmt.Println("SUCCEED")
}
