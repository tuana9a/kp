package util

import (
	"go.uber.org/zap"
)

var globalLogger *zap.Logger

func CreateLogger() *zap.Logger {
	logger, _ := zap.NewProduction()
	defer logger.Sync()
	return logger
}

func InitLogger() {
	globalLogger = CreateLogger()
}

func Log() *zap.Logger {
	return globalLogger
}
