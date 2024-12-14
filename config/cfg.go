package config

import (
	"encoding/json"
	"fmt"
	"strings"

	"github.com/tuana9a/kp/constants"
)

type Cfg struct {
	ProxmoxNode       string   `json:"proxmox_node"`
	ProxmoxHost       string   `json:"proxmox_host"`
	ProxmoxPort       int      `json:"proxmox_port,omitempty"`
	ProxmoxVerifySSL  bool     `json:"proxmox_verify_ssl,omitempty"`
	ProxmoxUser       string   `json:"proxmox_user,omitempty"`
	ProxmoxPassword   string   `json:"proxmox_password,omitempty"`
	ProxmoxTokenId    string   `json:"proxmox_token_id,omitempty"`
	ProxmoxTokenValue string   `json:"proxmox_token_value,omitempty"`
	VMIdRange         []int    `json:"vm_id_range,omitempty"`
	VMPreservedIDs    []int    `json:"vm_preserved_ids,omitempty"`
	VMPreservedIPs    []string `json:"vm_preserved_ips,omitempty"`
	VMSshKeys         string   `json:"vm_ssh_keys,omitempty"`
	VMNamePrefix      string   `json:"vm_name_prefix,omitempty"`
	LogLevel          string   `json:"log_level,omitempty"`
}

func (c *Cfg) String() string {
	var sb strings.Builder

	sb.WriteString("Cfg {\n")
	sb.WriteString(fmt.Sprintf("  ProxmoxNode: %q,\n", c.ProxmoxNode))
	sb.WriteString(fmt.Sprintf("  ProxmoxHost: %q,\n", c.ProxmoxHost))
	sb.WriteString(fmt.Sprintf("  ProxmoxPort: %d,\n", c.ProxmoxPort))
	sb.WriteString(fmt.Sprintf("  ProxmoxVerifySSL: %t,\n", c.ProxmoxVerifySSL))
	sb.WriteString(fmt.Sprintf("  ProxmoxUser: %q,\n", c.ProxmoxUser))
	sb.WriteString(fmt.Sprintf("  ProxmoxPassword: %q,\n", c.ProxmoxPassword))
	sb.WriteString(fmt.Sprintf("  ProxmoxTokenId: %q,\n", c.ProxmoxTokenId))
	sb.WriteString(fmt.Sprintf("  ProxmoxTokenValue: %q,\n", c.ProxmoxTokenValue))
	sb.WriteString(fmt.Sprintf("  VMIdRange: %v,\n", c.VMIdRange))
	sb.WriteString(fmt.Sprintf("  VMPreservedIDs: %v,\n", c.VMPreservedIDs))
	sb.WriteString(fmt.Sprintf("  VMPreservedIPs: %v,\n", c.VMPreservedIPs))
	sb.WriteString(fmt.Sprintf("  LogLevel: %q,\n", c.LogLevel))
	sb.WriteString("}")

	return sb.String()
}

func NewCfg(in []byte) *Cfg {
	var cfg Cfg
	err := json.Unmarshal(in, &cfg)
	if err != nil {
		panic(err)
	}
	if cfg.ProxmoxPort == 0 {
		cfg.ProxmoxPort = constants.DefaultProxmoxPort
	}
	if cfg.VMIdRange == nil {
		cfg.VMIdRange = constants.DefaultVMIdRange
	}
	if cfg.VMPreservedIDs == nil {
		cfg.VMPreservedIDs = constants.DefaultVMPreservedIDs
	}
	if cfg.VMPreservedIPs == nil {
		cfg.VMPreservedIPs = constants.DefaultVMPreservedIPs
	}
	return &cfg
}
