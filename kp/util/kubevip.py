from kp import template


def render_pod_manifest(inf: str, vip: str):
    manifest = template.KUBEVIP_MANIFEST_TEMPLATE.replace("$INTERFACE", inf).replace("$VIP", vip)
    return manifest
