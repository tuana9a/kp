package util

import "fmt"

func GetHomeDir(username string) string {
	if username == "root" {
		return "/root"
	}
	return fmt.Sprintf("/home/%s", username)
}
