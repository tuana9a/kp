package payload

type AddFlagsInput struct {
	Flags []string `json:"flags"`
}

type ApiserverFlag struct {
	Value   string
	Existed bool
}
