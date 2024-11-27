import json
import os

from kp import config


def load_config(config_path=None):
    if not config_path:
        if os.getenv("KP_CONFIG"):
            config_path = os.getenv("KP_CONFIG")
        else:
            config_path = os.path.join(os.getenv("HOME"), ".kp.config.json")
    print("config_path", config_path)
    if not os.path.exists(config_path):
        raise FileNotFoundError(config_path)
    with open(config_path, "r", encoding="utf-8") as f:
        return config.Cfg(**json.loads(f.read()))
