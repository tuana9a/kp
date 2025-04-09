package util

import (
	"go.uber.org/zap"
)

var log *zap.Logger
var sugar *zap.SugaredLogger

func CreateLogger() *zap.Logger {
	logger, _ := zap.NewProduction()
	defer logger.Sync()
	return logger
}

func InitLogger() {
	log = CreateLogger()
	sugar = log.Sugar()
}

func Log() *zap.Logger {
	return log
}

func Sugar() *zap.SugaredLogger {
	return sugar
}
