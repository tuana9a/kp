import os
import json
from app.logger import Logger

TIMEOUT_IN_SECONDS = 30 * 60  # 30 min
PROXMOX_VM_ID_RANGE = [100, 99999]
HAPROXY_BACKEND_NAME = "control-plane"  # TODO: configurable
PROXMOX_VM_TAG_DELIMITER = ";"


class Tag:
    lb = "k8s-lb"
    ctlpl = "k8s-ctlpl"
    wk = "k8s-wk"
    kp = "kp"


def load_config(config_path=os.getenv("KP_CONFIG"), log=Logger.DEBUG):
    log.info("config_path", config_path)
    if not config_path:
        raise ValueError("KP_CONFIG is not set")
    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)
    with open(config_path, "r") as f:
        return json.loads(f.read())
