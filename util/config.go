package util

import (
	"os"

	"github.com/tuana9a/kp/config"
)

func LoadConfig(configPath string) config.Cfg {
	blob, err := os.ReadFile(configPath)
	// fmt.Println(string(blob))
	if err != nil {
		panic(err)
	}
	var cfg = config.NewCfg(blob)
	return cfg
}
