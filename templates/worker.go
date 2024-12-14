package templates

import _ "embed"

//go:embed worker-setup-1.27.sh
var WorkerSetupScript127 string

//go:embed worker-setup-1.28.sh
var WorkerSetupScript128 string

//go:embed worker-setup-1.29.sh
var WorkerSetupScript129 string

//go:embed worker-setup-1.30.sh
var WorkerSetupScript130 string

var WorkderSetupScriptDefault = WorkerSetupScript130
