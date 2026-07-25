"""
NOCPing — ui/quick_ping_tab.py
Aba de ping rápido — diagnóstico ágil de host único.

Orquestrador fino: monta QuickPingControlPanel, QuickPingGraphPanel,
QuickPingConsole e QuickPingStatsPanel (ui/widgets/) e conecta o PingWorker
a eles. O estado de negócio (contadores, jitter, resultados) e o ciclo de
vida do worker continuam aqui — os widgets só renderizam o que recebem.
"""
import csv
import time
import statistics as _stats
from collections import deque

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QLabel, QFileDialog
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from core.models import PingResult, HostStatus
from core.workers import PingWorker
from .widgets._utils import rtt_color as _rtt_color
from .widgets.quick_ping_control_panel import QuickPingControlPanel
from .widgets.quick_ping_graph_panel import QuickPingGraphPanel
from .widgets.quick_ping_console import QuickPingConsole
from .widgets.quick_ping_stats_panel import QuickPingStatsPanel
from .theme.tokens import DARK


class QuickPingTab(QWidget):
    ping_finished = pyqtSignal(str, bool, str)
    host_status_changed = pyqtSignal(str, object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: PingWorker | None = None
        self._results: list[PingResult] = []
        self._console_count = 0

        # Contadores incrementais O(1)
        self._ok_count = 0
        self._total_count = 0
        self._sum_ms = 0.0
        self._min_ms = float("inf")
        self._max_ms = 0.0
        self._recent_rtts: deque[float] = deque(maxlen=50)

        self._resolved_ip = ""
        self._resolved_ver = ""
        self._start_time: float | None = None

        self._build_ui()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._control = QuickPingControlPanel()
        self._control.ping_requested.connect(self._on_ping_clicked)
        self._control.stop_requested.connect(self._stop)
        root.addWidget(self._control)

        # Estatísticas em destaque, largura cheia — logo abaixo do controle,
        # antes do gráfico (que agora não divide mais espaço horizontal com
        # elas, ver QuickPingGraphPanel abaixo).
        self._stats = QuickPingStatsPanel()
        root.addWidget(self._stats)

        # ── Splitter principal: gráfico (largura cheia) | console ────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: palette(mid);
                border-radius: 2px;
                margin: 2px 80px;
            }
        """)

        self._graph_panel = QuickPingGraphPanel()
        splitter.addWidget(self._graph_panel)

        self._console_panel = QuickPingConsole()
        self._console_panel.export_requested.connect(self._export_csv)
        splitter.addWidget(self._console_panel)

        # Proporções iniciais do splitter (70% gráfico, 30% console) — o
        # gráfico ganhou a área que antes dividia com o painel de stats.
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)

        root.addWidget(splitter, 1)

        # Placeholder quando vazio (nunca chega a ser adicionado a um layout
        # no fluxo original — mantido apenas por fidelidade de comportamento)
        self._placeholder = QLabel(
            "⚡ Ping Rápido\n\n"
            "Digite um host e pressione Enter ou clique em ⚡ Ping\n"
            "para iniciar um diagnóstico rápido."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color:#45475a; font-size:14px; line-height:1.8;"
        )
        self._placeholder.setVisible(False)

        # Timer para atualizar duração
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

    # ------------------------------------------------------------------
    # Controle
    # ------------------------------------------------------------------

    def _on_ping_clicked(self):
        host = self._control.host_text()
        if not host:
            self._control.focus_host()
            return
        # Para teste anterior se rodando
        self._kill_worker()
        self._console_panel.clear()
        self._start_ping(host)

    def _start_ping(self, host: str):
        self._reset_state()
        self._stats.set_status("INICIANDO…", DARK.info)
        self._control.set_running(True)

        self._console_panel.log_info(f"Iniciando ping para {host}...")

        cfg = self._control.build_config(host)

        self._start_time = time.monotonic()
        self._elapsed_timer.start()

        self._worker = PingWorker(cfg)
        self._worker.result.connect(self._on_result)
        self._worker.resolved.connect(self._on_resolved)
        self._worker.error.connect(self._on_error)
        self._worker.stats.connect(self._on_finished)
        self._worker.start()

    def _kill_worker(self):
        """Stop the running worker and disconnect its signals to prevent ghost callbacks."""
        if self._worker is not None:
            self._worker.result.disconnect(self._on_result)
            self._worker.resolved.disconnect(self._on_resolved)
            self._worker.error.disconnect(self._on_error)
            self._worker.stats.disconnect(self._on_finished)
            if self._worker.isRunning():
                self._worker.stop()
                self._worker.wait(1000)
            self._worker = None

    def _stop(self):
        was_running = self._worker is not None and self._worker.isRunning()
        self._kill_worker()
        if was_running:
            self._console_panel.log_info("Ping interrompido pelo usuário.")
        self._elapsed_timer.stop()
        self._stats.set_status("PARADO", DARK.text_muted)
        self._control.set_running(False)

    def _reset_state(self):
        self._results.clear()
        self._ok_count = 0
        self._total_count = 0
        self._sum_ms = 0.0
        self._min_ms = float("inf")
        self._max_ms = 0.0
        self._recent_rtts.clear()
        self._resolved_ip = ""
        self._resolved_ver = ""
        self._start_time = None
        self._last_status = None
        self._graph_panel.reset()
        self._stats.reset_display()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_resolved(self, ip: str, version: str):
        self._resolved_ip = ip
        self._resolved_ver = version
        self._stats.set_resolved(f"{ip}  [{version}]")
        self._console_panel.log_info(f"Resolvido: {ip} [{version}]")

    def _on_result(self, r: PingResult):
        self._results.append(r)
        timeout = not r.success or r.elapsed_ms <= 0
        self._graph_panel.add_point(r.elapsed_ms if not timeout else 0.0, timeout)

        # Contadores O(1)
        self._total_count += 1
        if r.success and r.elapsed_ms > 0:
            self._ok_count += 1
            self._sum_ms += r.elapsed_ms
            self._recent_rtts.append(r.elapsed_ms)
            if r.elapsed_ms < self._min_ms:
                self._min_ms = r.elapsed_ms
            if r.elapsed_ms > self._max_ms:
                self._max_ms = r.elapsed_ms

        # Status
        new_status = HostStatus.UP if r.success else HostStatus.DOWN
        if getattr(self, "_last_status", None) != new_status:
            old_status = getattr(self, "_last_status", None)
            if old_status is not None:
                host = self._control.host_text()
                self.host_status_changed.emit(host, old_status, new_status)
            self._last_status = new_status

        if r.success:
            self._stats.set_status("ONLINE", DARK.success)
        else:
            self._stats.set_status("TIMEOUT", DARK.danger)

        # RTT atual
        if r.success:
            c = _rtt_color(r.elapsed_ms)
            self._stats.set_rtt(f"{r.elapsed_ms:.1f} ms", c)
        else:
            self._stats.set_rtt("timeout", DARK.danger, font_size=16)

        # Estatísticas
        self._update_stats()

        # Seq
        self._stats.set_seq(str(r.seq))

        # Console log
        mode = self._control.current_mode().value
        port_info = f":{self._control.current_port()}" if mode != "ICMP" else ""
        ip = self._resolved_ip or self._control.host_text()
        self._console_panel.log_result(r, mode, port_info, ip)

    def _on_error(self, msg: str):
        self._stats.set_status("ERRO", DARK.warning)
        self._console_panel.log_error(msg)
        self._control.set_running(False)
        self._elapsed_timer.stop()

        # Paridade com o Monitor (HostCard._set_status): erro de
        # configuração/privilégio (ex. ICMP/UDP sem admin) também notifica
        # a bandeja, não só transições DOWN/UP de _on_result(). Ao contrário
        # de _on_result(), não suprime a primeira observação -- um erro
        # normalmente É a primeira (e única) coisa que acontece na sessão
        # de ping, então esperar uma "segunda mudança" nunca notificaria.
        old_status = getattr(self, "_last_status", None)
        if old_status != HostStatus.ERROR:
            host = self._control.host_text()
            self.host_status_changed.emit(host, old_status, HostStatus.ERROR)
            self._last_status = HostStatus.ERROR

    def _on_finished(self, stats: dict):
        self._elapsed_timer.stop()
        self._update_elapsed()
        self._control.set_running(False)

        total = self._total_count
        ok = self._ok_count
        lost = total - ok
        self._console_panel.log_info(
            f"Concluído: {total} enviados, {ok} recebidos, "
            f"{lost} perdidos ({lost/total*100:.1f}% perda)"
            if total > 0 else "Concluído: nenhum pacote enviado."
        )

        if total > 0 and self._ok_count > 0:
            self._stats.set_status("CONCLUÍDO", DARK.success)
            success = True
        elif total > 0:
            self._stats.set_status("CONCLUÍDO", DARK.danger)
            success = False
        else:
            self._stats.set_status("CONCLUÍDO", DARK.text_muted)
            success = False

        if total > 0:
            avg = self._sum_ms / ok if ok else 0.0
            lost = total - ok
            loss_pct = lost / total * 100
            if success:
                msg = f"Média: {avg:.1f}ms | Perda: {loss_pct:.1f}%"
            else:
                msg = f"Host inalcançável ({loss_pct:.1f}% de perda)"
            host = self._control.host_text()
            self.ping_finished.emit(host, success, msg)

    # ------------------------------------------------------------------
    # Stats helpers
    # ------------------------------------------------------------------

    def _update_stats(self):
        ok = self._ok_count
        total = self._total_count
        lost = total - ok
        loss_pct = lost / total * 100 if total else 0.0
        avg = self._sum_ms / ok if ok else 0.0
        mn = self._min_ms if ok else 0.0
        mx = self._max_ms if ok else 0.0

        # Jitter (stdev dos últimos RTTs)
        if len(self._recent_rtts) > 1:
            jitter = _stats.stdev(self._recent_rtts)
        else:
            jitter = 0.0

        # Média
        if ok:
            self._stats.set_avg(f"{avg:.1f} ms", _rtt_color(avg))
        else:
            self._stats.set_avg("—", DARK.text_muted)

        # Min
        if ok:
            self._stats.set_min(f"{mn:.1f} ms", _rtt_color(mn))
        else:
            self._stats.set_min("—", DARK.text_muted)

        # Max
        if ok:
            self._stats.set_max(f"{mx:.1f} ms", _rtt_color(mx))
        else:
            self._stats.set_max("—", DARK.text_muted)

        # Loss
        loss_c = DARK.danger if loss_pct > 5 else (DARK.warning if loss_pct > 0 else DARK.success)
        self._stats.set_loss(f"{loss_pct:.1f}%", loss_c)

        # Jitter
        if ok:
            jit_c = _rtt_color(jitter * 2)  # jitter tends to be smaller, scale for color
            self._stats.set_jitter(f"{jitter:.1f} ms", jit_c)
        else:
            self._stats.set_jitter("—", DARK.text_muted)

    def _update_elapsed(self):
        if self._start_time is None:
            return
        elapsed = time.monotonic() - self._start_time
        mins, secs = divmod(int(elapsed), 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            txt = f"{hours}h {mins:02d}m {secs:02d}s"
        elif mins > 0:
            txt = f"{mins}m {secs:02d}s"
        else:
            txt = f"{secs}s"
        self._stats.set_elapsed(txt)

    # ------------------------------------------------------------------
    # Exportação
    # ------------------------------------------------------------------

    def _export_csv(self):
        if not self._results:
            return
        host = self._control.host_text().replace(":", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Quick Ping CSV",
            f"quickping_{host}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Seq", "Sucesso", "RTT (ms)", "Nota"])
            for r in self._results:
                writer.writerow([r.seq, r.success, f"{r.elapsed_ms:.3f}", r.note])

    # ------------------------------------------------------------------
    # Tema / Cleanup
    # ------------------------------------------------------------------

    def apply_theme(self, dark: bool):
        """Called by MainWindow when theme changes."""
        self._console_panel.apply_theme(dark)
        self._graph_panel.apply_theme(dark)

    def cleanup(self):
        """Stop worker for shutdown."""
        self._elapsed_timer.stop()
        self._kill_worker()
