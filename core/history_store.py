"""
NOCPing — core/history_store.py
Armazena histórico de RTT por host em SQLite (stdlib).
"""
import sqlite3
import threading
import time
from pathlib import Path

from .models import PingResult

_DB_PATH = Path(__file__).parent.parent / "nocping_history.db"

_DDL = """
CREATE TABLE IF NOT EXISTS rtt_history (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    host     TEXT    NOT NULL,
    ts       REAL    NOT NULL,
    success  INTEGER NOT NULL,
    elapsed  REAL    NOT NULL,
    note     TEXT
);
CREATE INDEX IF NOT EXISTS idx_host_ts ON rtt_history(host, ts);
"""


class HistoryStore:
    _instance: "HistoryStore | None" = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "HistoryStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._conn = sqlite3.connect(
            str(_DB_PATH), check_same_thread=False
        )
        self._conn.executescript(_DDL)
        self._conn.commit()
        self._rw_lock = threading.Lock()

    def record(self, host: str, result: PingResult) -> None:
        with self._rw_lock:
            self._conn.execute(
                "INSERT INTO rtt_history(host, ts, success, elapsed, note) "
                "VALUES (?, ?, ?, ?, ?)",
                (host, time.time(), int(result.success),
                 result.elapsed_ms, result.note),
            )
            self._conn.commit()

    def query(self, host: str, last_n: int = 500) -> list[dict]:
        with self._rw_lock:
            cur = self._conn.execute(
                "SELECT ts, success, elapsed, note FROM rtt_history "
                "WHERE host = ? ORDER BY ts DESC LIMIT ?",
                (host, last_n),
            )
            rows = cur.fetchall()
        return [
            {"ts": r[0], "success": bool(r[1]), "elapsed": r[2], "note": r[3]}
            for r in reversed(rows)
        ]

    def clear(self, host: str) -> None:
        with self._rw_lock:
            self._conn.execute(
                "DELETE FROM rtt_history WHERE host = ?", (host,)
            )
            self._conn.commit()

    def hosts(self) -> list[str]:
        with self._rw_lock:
            cur = self._conn.execute(
                "SELECT DISTINCT host FROM rtt_history ORDER BY host"
            )
            return [r[0] for r in cur.fetchall()]
