"""
Testes de core/history_store.py (sem rede, sem GUI).
Usa banco em memória para não poluir nocping_history.db.
"""
import threading
import time
import sqlite3
import pytest

from core.models import PingResult


# Fixture: instância isolada com banco em memória
@pytest.fixture
def store(tmp_path, monkeypatch):
    import core.history_store as hs
    monkeypatch.setattr(hs, "_DB_PATH", tmp_path / "test.db")
    hs.HistoryStore._instance = None          # reset singleton
    instance = hs.HistoryStore.instance()
    yield instance
    hs.HistoryStore._instance = None


def _ok(ms: float) -> PingResult:
    return PingResult(seq=1, success=True, elapsed_ms=ms, note="")


def _fail() -> PingResult:
    return PingResult(seq=2, success=False, elapsed_ms=0.0, note="timeout")


# ---------------------------------------------------------------------------

def test_record_and_query_round_trip(store):
    store.record("8.8.8.8", _ok(10.0))
    rows = store.query("8.8.8.8")
    assert len(rows) == 1
    assert rows[0]["success"] is True
    assert abs(rows[0]["elapsed"] - 10.0) < 0.001


def test_query_returns_chronological_order(store):
    for ms in [10.0, 20.0, 30.0]:
        store.record("host1", _ok(ms))
    rows = store.query("host1")
    elapsed = [r["elapsed"] for r in rows]
    assert elapsed == sorted(elapsed)


def test_query_respects_last_n_limit(store):
    for i in range(20):
        store.record("host2", _ok(float(i)))
    rows = store.query("host2", last_n=5)
    assert len(rows) == 5
    # deve retornar os 5 mais recentes
    assert rows[-1]["elapsed"] == 19.0


def test_failed_result_stored_correctly(store):
    store.record("host3", _fail())
    rows = store.query("host3")
    assert rows[0]["success"] is False
    assert rows[0]["elapsed"] == 0.0
    assert rows[0]["note"] == "timeout"


def test_clear_removes_only_target_host(store):
    store.record("hostA", _ok(1.0))
    store.record("hostB", _ok(2.0))
    store.clear("hostA")
    assert store.query("hostA") == []
    assert len(store.query("hostB")) == 1


def test_hosts_lists_all_distinct_hosts(store):
    store.record("alpha", _ok(1.0))
    store.record("beta", _ok(2.0))
    store.record("alpha", _ok(3.0))
    assert sorted(store.hosts()) == ["alpha", "beta"]


def test_query_empty_host_returns_empty(store):
    assert store.query("nonexistent") == []


def test_ts_is_recent(store):
    before = time.time()
    store.record("tshost", _ok(5.0))
    after = time.time()
    rows = store.query("tshost")
    assert before <= rows[0]["ts"] <= after


def test_thread_safety(store):
    errors = []

    def worker(host, n):
        try:
            for i in range(n):
                store.record(host, _ok(float(i)))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(f"h{i}", 50))
               for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    total = sum(len(store.query(f"h{i}", 999)) for i in range(4))
    assert total == 200
