package main_test

import (
	"bytes"
	"testing"
	"text/template"

	"github.com/tuana9a/kp/payload"
)

const tmpl = `[Service]
ExecStart=/usr/local/bin/containerd
{{range .Containerd.Envs}}Environment={{.}}
{{end}}`

func TestContainerdTemplateEmpty(t *testing.T) {
	render, _ := template.New("kubesetup").Parse(tmpl)
	var b bytes.Buffer
	render.Execute(&b, payload.ContainerdSetupTemplate{
		Envs: []string{},
	})
	result := b.String()
	expected := `[Service]
ExecStart=/usr/local/bin/containerd
`
	if result != expected {
		t.Errorf("result\n'%s'\nexpected\n'%s'", result, expected)
	}
}

func TestKubesetupTemplateNotEmpty(t *testing.T) {
	render, _ := template.New("kubesetup").Parse(tmpl)
	var b bytes.Buffer
	render.Execute(&b, payload.ContainerdSetupTemplate{
		Envs: []string{"hello=world", "world=champion"},
	})
	result := b.String()
	expected := `[Service]
ExecStart=/usr/local/bin/containerd
Environment=hello=world
Environment=world=champion
`
	if result != expected {
		t.Errorf("result\n'%s'\nexpected\n'%s'", result, expected)
	}
}
