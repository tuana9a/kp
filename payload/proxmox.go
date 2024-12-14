package payload

type AgentFileRead struct {
	Content   string `json:"content"`
	Truncated bool   `json:"truncated"`
}
