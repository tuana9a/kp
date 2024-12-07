package util

import "go.uber.org/zap"

func CreateLogger(level string) *zap.Logger {
	zLevel, _ := zap.ParseAtomicLevel(level)
	var cfg = zap.Config{
		Level:    zLevel,
		Encoding: "json",
	}
	logger := zap.Must(cfg.Build())
	defer logger.Sync()
	return logger
}
