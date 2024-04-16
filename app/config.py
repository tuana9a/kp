import os
import json
from app.logger import Logger

TIMEOUT_IN_SECONDS = 30 * 60  # 30 min
PROXMOX_VM_ID_RANGE = [100, 99999]
HAPROXY_BACKEND_NAME = "control-plane"  # TODO: configurable
PROXMOX_VM_TAG_DELIMITER = ";"
HAPROXY_CONFIG_LOCATION = "/etc/haproxy/haproxy.cfg"
HAPROXY_CONFIG_TEMPLATE = """# DO NOT EDIT (generated from https://gitlab.com/tuana9a/kp)
defaults
    log     global
    mode    http
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000
    errorfile 400 /etc/haproxy/errors/400.http
    errorfile 403 /etc/haproxy/errors/403.http
    errorfile 408 /etc/haproxy/errors/408.http
    errorfile 500 /etc/haproxy/errors/500.http
    errorfile 502 /etc/haproxy/errors/502.http
    errorfile 503 /etc/haproxy/errors/503.http
    errorfile 504 /etc/haproxy/errors/504.http

frontend api-server
    mode tcp
    bind 0.0.0.0:6443
    default_backend control-plane

backend control-plane
    mode tcp
    option httpchk GET /healthz
    http-check expect status 200
    option ssl-hello-chk
    balance leastconn
{backends}
"""


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
