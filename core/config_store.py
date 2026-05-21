"""
NOCPing — core/config_store.py
Persiste e restaura a lista de hosts monitorados em nocping_hosts.json.
"""
import json
import os

from .models import ProbeConfig, ProbeMode, IPVersion

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "nocping_hosts.json")


def save_hosts(cards) -> None:
    data = [
        {
            "host":        c.config.host,
            "port":        c.config.port,
            "mode":        c.config.mode.value,
            "ip_version":  c.config.ip_version.value,
            "timeout_ms":  c.config.timeout_ms,
            "interval_ms": c.config.interval_ms,
        }
        for c in cards
    ]
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_hosts() -> list[ProbeConfig]:
    if not os.path.exists(_CONFIG_PATH):
        return []
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        configs = []
        for d in data:
            configs.append(ProbeConfig(
                host=d["host"],
                port=d.get("port", 443),
                mode=ProbeMode(d.get("mode", "TCP")),
                ip_version=IPVersion(d.get("ip_version", "Auto")),
                timeout_ms=d.get("timeout_ms", 2000),
                interval_ms=d.get("interval_ms", 1000),
            ))
        return configs
    except Exception:
        return []
