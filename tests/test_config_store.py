import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from core.models import ProbeConfig, ProbeMode, IPVersion


def _fake_card(host, port=443, mode=ProbeMode.TCP,
               ip_version=IPVersion.AUTO, timeout_ms=2000, interval_ms=1000):
    class Card:
        config = ProbeConfig(
            host=host, port=port, mode=mode,
            ip_version=ip_version, timeout_ms=timeout_ms, interval_ms=interval_ms,
        )
    return Card()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    import core.config_store as cs
    monkeypatch.setattr(cs, "_CONFIG_PATH", str(tmp_path / "hosts.json"))
    return cs


def test_load_returns_empty_when_no_file(isolated_config):
    assert isolated_config.load_hosts() == []


def test_round_trip_single_host(isolated_config):
    isolated_config.save_hosts([_fake_card("8.8.8.8")])
    loaded = isolated_config.load_hosts()
    assert len(loaded) == 1
    c = loaded[0]
    assert c.host == "8.8.8.8"
    assert c.port == 443
    assert c.mode == ProbeMode.TCP
    assert c.ip_version == IPVersion.AUTO
    assert c.timeout_ms == 2000
    assert c.interval_ms == 1000


def test_round_trip_preserves_order(isolated_config):
    hosts = ["1.1.1.1", "8.8.8.8", "192.168.1.1"]
    isolated_config.save_hosts([_fake_card(h) for h in hosts])
    loaded = isolated_config.load_hosts()
    assert [c.host for c in loaded] == hosts


def test_round_trip_all_modes(isolated_config):
    cards = [_fake_card("h", mode=m) for m in ProbeMode]
    isolated_config.save_hosts(cards)
    loaded = isolated_config.load_hosts()
    assert [c.mode for c in loaded] == list(ProbeMode)


def test_round_trip_all_ip_versions(isolated_config):
    cards = [_fake_card("h", ip_version=v) for v in IPVersion]
    isolated_config.save_hosts(cards)
    loaded = isolated_config.load_hosts()
    assert [c.ip_version for c in loaded] == list(IPVersion)


def test_save_overwrites_previous(isolated_config):
    isolated_config.save_hosts([_fake_card("old.host")])
    isolated_config.save_hosts([_fake_card("new.host")])
    loaded = isolated_config.load_hosts()
    assert len(loaded) == 1
    assert loaded[0].host == "new.host"


def test_save_empty_list_clears_config(isolated_config):
    isolated_config.save_hosts([_fake_card("x")])
    isolated_config.save_hosts([])
    assert isolated_config.load_hosts() == []


def test_load_returns_empty_on_corrupt_json(isolated_config):
    with open(isolated_config._CONFIG_PATH, "w") as f:
        f.write("{broken json[[")
    assert isolated_config.load_hosts() == []


def test_load_returns_list_on_wrong_structure(isolated_config):
    with open(isolated_config._CONFIG_PATH, "w") as f:
        json.dump({"not": "a list"}, f)
    result = isolated_config.load_hosts()
    assert isinstance(result, list)


def test_load_skips_entries_with_missing_host(isolated_config):
    data = [{"port": 80, "mode": "TCP", "ip_version": "Auto"}]
    with open(isolated_config._CONFIG_PATH, "w") as f:
        json.dump(data, f)
    result = isolated_config.load_hosts()
    assert isinstance(result, list)


def test_round_trip_preserves_timeout_and_interval(isolated_config):
    isolated_config.save_hosts([_fake_card("x", timeout_ms=5000, interval_ms=500)])
    loaded = isolated_config.load_hosts()
    assert loaded[0].timeout_ms == 5000
    assert loaded[0].interval_ms == 500
