package util

import (
	"crypto/tls"
	"errors"
	"fmt"
	"net/http"
	"net/url"

	"github.com/luthermonson/go-proxmox"
	"github.com/tuana9a/kp/config"
)

func CreateProxmoxClient(cfg *config.Cfg) (*proxmox.Client, error) {
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
		return client, nil
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
		return client, nil
	}

	return nil, errors.New("can not detect any authentication method")
}

func EncodeSshKeys(content string) string {
	return url.QueryEscape(content)
}
