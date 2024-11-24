package util

import (
	"context"
	"crypto/tls"
	"fmt"
	"net/http"
	"time"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/config"
)

func CreateProxmoxClient(cfg config.Cfg) *proxmox.Client {
	insecureHTTPClient := http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				InsecureSkipVerify: true,
			},
		},
	}
	var client *proxmox.Client = nil
	if cfg.ProxmoxTokenId != "" {
		client = proxmox.NewClient(fmt.Sprintf("https://%s:%d/api2/json", cfg.ProxmoxHost, cfg.ProxmoxPort),
			proxmox.WithHTTPClient(&insecureHTTPClient),
			proxmox.WithAPIToken(cfg.ProxmoxTokenId, cfg.ProxmoxTokenValue),
		)
	}
	if cfg.ProxmoxUser != "" {
		credentials := proxmox.Credentials{
			Username: cfg.ProxmoxUser,
			Password: cfg.ProxmoxPassword,
		}
		client = proxmox.NewClient(fmt.Sprintf("https://%s:%d/api2/json", cfg.ProxmoxHost, cfg.ProxmoxPort),
			proxmox.WithHTTPClient(&insecureHTTPClient),
			proxmox.WithCredentials(&credentials),
		)
	}

	version, err := client.Version(context.Background())
	if err != nil {
		panic(err)
	}
	fmt.Println("proxmox-api version: ", version.Version)
	return client
}

func WaitForCloudInitToComplete(ctx context.Context, vm *proxmox.VirtualMachine, max int) {
	timeout := time.After(time.Duration(max) * time.Second)
	
}
