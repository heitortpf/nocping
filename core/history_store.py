"""
NOCPing — core/history_store.py
Armazena histórico de RTT por host em SQLite (stdlib).
"""
import sqlite3
import threading
import time
import queue
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

_BATCH_SIZE = 50  # flush automático a cada N registros


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
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_DDL)
        self._conn.commit()
        
        self._rw_lock = threading.Lock()
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._db_worker, daemon=True)
        self._worker_thread.start()

    def _db_worker(self):
        batch = []
        while not self._stop_event.is_set():
            try:
                # Espera até 0.5s por um item novo
                item = self._queue.get(timeout=0.5)
                batch.append(item)
            except queue.Empty:
                pass
            
            # Esvazia a fila rapidamente para o batch atual
            while len(batch) < _BATCH_SIZE:
                try:
                    batch.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            
            if batch:
                with self._rw_lock:
                    self._conn.executemany(
                        "INSERT INTO rtt_history(host, ts, success, elapsed, note) "
                        "VALUES (?, ?, ?, ?, ?)",
                        batch
                    )
                    self._conn.commit()
                # Libera as tasks no queue.join()
                for _ in range(len(batch)):
                    self._queue.task_done()
                batch.clear()

    def record(self, host: str, result: PingResult) -> None:
        """Adiciona registro à fila sem bloquear (O(1))."""
        self._queue.put((
            host, time.time(), int(result.success),
            result.elapsed_ms, result.note,
        ))

    def flush(self) -> None:
        """Aguarda todos os registros pendentes serem salvos."""
        self._queue.join()

    def query(self, host: str, last_n: int = 500) -> list[dict]:
        self.flush()
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
        self.flush()
        with self._rw_lock:
            self._conn.execute(
                "DELETE FROM rtt_history WHERE host = ?", (host,)
            )
            self._conn.commit()

    def hosts(self) -> list[str]:
        self.flush()
        with self._rw_lock:
            cur = self._conn.execute(
                "SELECT DISTINCT host FROM rtt_history ORDER BY host"
            )
            return [r[0] for r in cur.fetchall()]

    def close(self) -> None:
        """Encerra worker, processa pendentes e fecha conexão SQLite."""
        self._stop_event.set()
        self._worker_thread.join(timeout=2.0)
        self.flush()
        with self._rw_lock:
            self._conn.close()


