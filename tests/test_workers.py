import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch
from core.models import ProbeConfig, ProbeMode, IPVersion, PingResult


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _flush(app):
    """Drena a fila de eventos Qt para que sinais queued sejam entregues."""
    app.processEvents()


def _tcp_cfg(**kw):
    defaults = dict(
        host="127.0.0.1", port=80, mode=ProbeMode.TCP,
        ip_version=IPVersion.AUTO, timeout_ms=500, interval_ms=50,
    )
    defaults.update(kw)
    return ProbeConfig(**defaults)


# ---------------------------------------------------------------------------
# PingWorker
# ---------------------------------------------------------------------------

class TestPingWorker:

    def test_stop_is_prompt_with_event_wait(self, qapp):
        """Event.wait deve acordar imediatamente no stop(), < 200ms mesmo com interval_ms=5000."""
        from core.workers import PingWorker
        cfg = _tcp_cfg(interval_ms=5000)
        fake = PingResult(seq=1, success=True, elapsed_ms=1.0)

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.tcp_ping_once", return_value=fake):
            w = PingWorker(cfg)
            w.start()
            time.sleep(0.05)          # entra no Event.wait(5s)
            t0 = time.perf_counter()
            w.stop()
            w.wait(1000)
            elapsed_ms = (time.perf_counter() - t0) * 1000

        assert elapsed_ms < 200, (
            f"Worker levou {elapsed_ms:.0f}ms para parar — Event.wait não está funcionando"
        )

    def test_stop_before_start_does_not_raise(self, qapp):
        from core.workers import PingWorker
        w = PingWorker(_tcp_cfg())
        w.stop()  # não deve lançar exceção

    def test_emits_result_signal(self, qapp):
        from core.workers import PingWorker
        from PyQt6.QtCore import Qt
        cfg = _tcp_cfg(count=1, interval_ms=10)
        fake = PingResult(seq=1, success=True, elapsed_ms=3.5)
        received = []

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.tcp_ping_once", return_value=fake):
            w = PingWorker(cfg)
            w.result.connect(lambda r: received.append(r),
                             Qt.ConnectionType.DirectConnection)
            w.start()
            w.wait(2000)
        _flush(qapp)

        assert len(received) == 1
        assert received[0].success is True
        assert received[0].elapsed_ms == pytest.approx(3.5)

    def test_emits_stats_after_count_reached(self, qapp):
        from core.workers import PingWorker
        from PyQt6.QtCore import Qt
        cfg = _tcp_cfg(count=3, interval_ms=10)
        fake = PingResult(seq=1, success=True, elapsed_ms=10.0)
        stats_list = []

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.tcp_ping_once", return_value=fake):
            w = PingWorker(cfg)
            w.stats.connect(lambda s: stats_list.append(s),
                            Qt.ConnectionType.DirectConnection)
            w.start()
            w.wait(3000)
        _flush(qapp)

        assert len(stats_list) == 1
        s = stats_list[0]
        assert s["total"] == 3
        assert s["received"] == 3
        assert s["loss_pct"] == pytest.approx(0.0)

    def test_counts_losses_in_stats(self, qapp):
        from core.workers import PingWorker
        from PyQt6.QtCore import Qt
        cfg = _tcp_cfg(count=4, interval_ms=10)
        results_cycle = [
            PingResult(1, True,  10.0),
            PingResult(2, False, 0.0),
            PingResult(3, True,  20.0),
            PingResult(4, False, 0.0),
        ]
        counter = [0]
        stats_list = []

        def fake_ping(*_a, **_kw):
            r = results_cycle[counter[0] % len(results_cycle)]
            counter[0] += 1
            return r

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.tcp_ping_once", side_effect=fake_ping):
            w = PingWorker(cfg)
            w.stats.connect(lambda s: stats_list.append(s),
                            Qt.ConnectionType.DirectConnection)
            w.start()
            w.wait(3000)
        _flush(qapp)

        assert stats_list[0]["loss_pct"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# ScanWorker
# ---------------------------------------------------------------------------

class TestScanWorker:

    def test_emits_all_port_results_including_closed(self, qapp):
        """ScanWorker emite ALL port_result — filtragem é responsabilidade da UI."""
        from core.workers import ScanWorker
        from PyQt6.QtCore import Qt
        all_results = []

        def fake_scan(ip, family, ports, timeout_ms, max_threads,
                      stop_event, on_result, protocol):
            on_result(80,  True,  1.2, "TCP")
            on_result(443, True,  0.8, "TCP")
            on_result(22,  False, 0.0, "TCP")

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.scan_ports", side_effect=fake_scan):
            w = ScanWorker("127.0.0.1", "80,443,22", IPVersion.AUTO,
                           timeout_ms=500, max_threads=10, protocol="TCP")
            w.port_result.connect(
                lambda p, ok, ms, proto: all_results.append((p, ok)),
                Qt.ConnectionType.DirectConnection,
            )
            w.start()
            w.wait(2000)
        _flush(qapp)

        assert (80,  True)  in all_results
        assert (443, True)  in all_results
        assert (22,  False) in all_results   # worker emite tudo; UI que filtra

    def test_progress_reaches_100_percent(self, qapp):
        from core.workers import ScanWorker
        from PyQt6.QtCore import Qt
        progress_events = []

        def fake_scan(ip, family, ports, timeout_ms, max_threads,
                      stop_event, on_result, protocol):
            for p in ports:
                on_result(p, True, 1.0, "TCP")

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.scan_ports", side_effect=fake_scan):
            w = ScanWorker("127.0.0.1", "80,443,8080", IPVersion.AUTO,
                           timeout_ms=500, max_threads=10, protocol="TCP")
            w.progress.connect(
                lambda d, t: progress_events.append((d, t)),
                Qt.ConnectionType.DirectConnection,
            )
            w.start()
            w.wait(2000)
        _flush(qapp)

        assert len(progress_events) > 0
        last_done, last_total = progress_events[-1]
        assert last_done == last_total

    def test_emits_error_on_unresolvable_host(self, qapp):
        from core.workers import ScanWorker
        from PyQt6.QtCore import Qt
        errors = []

        with patch("core.workers.resolve_host", side_effect=OSError("name not found")):
            w = ScanWorker("bad.host.invalid", "80", IPVersion.AUTO,
                           timeout_ms=500, max_threads=1, protocol="TCP")
            w.error.connect(errors.append, Qt.ConnectionType.DirectConnection)
            w.start()
            w.wait(2000)
        _flush(qapp)

        assert len(errors) == 1
        assert errors[0] != ""

    def test_tcp_plus_udp_doubles_total(self, qapp):
        """Para TCP+UDP, total de progresso deve ser 2× o número de portas."""
        from core.workers import ScanWorker
        from PyQt6.QtCore import Qt
        progress_events = []

        def fake_scan(ip, family, ports, timeout_ms, max_threads,
                      stop_event, on_result, protocol):
            for p in ports:
                on_result(p, True, 1.0, protocol)

        with patch("core.workers.resolve_host", return_value=(2, "127.0.0.1")), \
             patch("core.workers.scan_ports", side_effect=fake_scan):
            w = ScanWorker("127.0.0.1", "80,443", IPVersion.AUTO,
                           timeout_ms=500, max_threads=10, protocol="TCP+UDP")
            w.progress.connect(
                lambda d, t: progress_events.append((d, t)),
                Qt.ConnectionType.DirectConnection,
            )
            w.start()
            w.wait(2000)
        _flush(qapp)

        assert len(progress_events) > 0
        _, total = progress_events[-1]
        assert total == 4  # 2 portas × 2 protocolos
