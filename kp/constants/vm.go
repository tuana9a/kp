package constants

const (
	DefaultProxmoxPort      = 8006
	DefaultProxmoxVerifySSL = false
	DefaultVMNamePrefix     = "i-"
)

var (
	DefaultVMIdRange      = []int{100, 999}
	DefaultVMPreservedIDs = []int{}
	DefaultVMPreservedIPs = []string{}
)

var CloudInitStatusWaitCmd = []string{"cloud-init", "status", "--wait"}
var CloudInitStatusCmd = []string{"cloud-init", "status"}
