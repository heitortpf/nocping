"""
NOCPing — ui/quick_ping_tab.py
Aba de ping rápido — diagnóstico ágil de host único.
"""
import csv
import time
import statistics as _stats
from collections import deque
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit,
    QSpinBox, QComboBox, QPushButton, QLabel, QFrame,
    QPlainTextEdit, QSplitter, QFileDialog, QSizePolicy,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCursor

from core.models import ProbeConfig, ProbeMode, IPVersion, PingResult
from core.workers import PingWorker
from .widgets.rtt_graph import RttGraph
from .widgets._utils import field_label as _lbl, rtt_color as _rtt_color


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STAT_LABEL_STYLE = "color:#6b7280; font-size:10px; letter-spacing:0.5px;"

_CONSOLE_STYLE_DARK = """
    QPlainTextEdit {
        background: #11111b;
        color: #cdd6f4;
        border: 1px solid #313244;
        border-radius: 6px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        padding: 6px;
        selection-background-color: #7c3aed;
    }
"""

_CONSOLE_STYLE_LIGHT = """
    QPlainTextEdit {
        background: #ffffff;
        color: #4c4f69;
        border: 1px solid #bcc0cc;
        border-radius: 6px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 12px;
        padding: 6px;
        selection-background-color: #7c3aed;
        selection-color: #ffffff;
    }
"""

_TOOLBAR_BTN = (
    "QPushButton{background:palette(button);color:palette(button-text);"
    "border-radius:4px;font-size:11px;border:none;padding:2px 10px;}"
    "QPushButton:hover{background:palette(mid);}"
)

_PRIMARY_BTN = (
    "QPushButton{background:#7c3aed;color:#fff;border-radius:6px;"
    "font-size:13px;font-weight:bold;border:none;padding:0 20px;}"
    "QPushButton:hover{background:#6d28d9;}"
    "QPushButton:pressed{background:#5b21b6;}"
    "QPushButton:disabled{background:palette(button);color:palette(placeholder-text);}"
)

_STOP_BTN = (
    "QPushButton{background:#dc2626;color:#fff;border-radius:6px;"
    "font-size:13px;font-weight:bold;border:none;padding:0 20px;}"
    "QPushButton:hover{background:#b91c1c;}"
    "QPushButton:disabled{background:palette(button);color:palette(placeholder-text);}"
)


def _stat_value(text: str = "—") -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:palette(mid); margin:0;")
    f.setFixedHeight(1)
    return f


# ---------------------------------------------------------------------------
# QuickPingTab
# ---------------------------------------------------------------------------

class QuickPingTab(QWidget):
    MAX_CONSOLE_LINES = 5000

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
        root.setSpacing(0)

        # ── Painel de controles ─────────────────────────────────────
        panel = QFrame()
        panel.setObjectName("QPPanel")
        panel.setStyleSheet("""
            #QPPanel {
                background: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(14, 10, 14, 10)
        panel_layout.setSpacing(8)

        # Linha 0: rótulos
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)  # host — expansível

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("PORTA"), 0, 1)
        grid.addWidget(_lbl("MODO"), 0, 2)
        grid.addWidget(_lbl("VERSÃO IP"), 0, 3)
        grid.addWidget(_lbl("CONTAGEM"), 0, 4)
        grid.addWidget(_lbl("TIMEOUT"), 0, 5)
        grid.addWidget(_lbl("INTERVALO"), 0, 6)

        # Linha 1: campos
        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("ex: 8.8.8.8, google.com, 2001:4860:4860::8888")
        self._inp_host.setFixedHeight(34)
        self._inp_host.setMinimumWidth(180)
        self._inp_host.returnPressed.connect(self._on_ping_clicked)

        self._inp_port = QSpinBox()
        self._inp_port.setRange(1, 65535)
        self._inp_port.setValue(443)
        self._inp_port.setFixedHeight(34)
        self._inp_port.setFixedWidth(85)

        self._cmb_mode = QComboBox()
        for m in ProbeMode:
            self._cmb_mode.addItem(m.value, m)
        self._cmb_mode.setFixedHeight(34)
        self._cmb_mode.setFixedWidth(90)
        self._cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self._cmb_mode.setCurrentIndex(self._cmb_mode.findData(ProbeMode.ICMP))

        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedHeight(34)
        self._cmb_ip.setFixedWidth(80)

        self._inp_count = QSpinBox()
        self._inp_count.setRange(0, 99999)
        self._inp_count.setValue(0)
        self._inp_count.setFixedHeight(34)
        self._inp_count.setFixedWidth(75)
        self._inp_count.setSpecialValueText("∞")
        self._inp_count.setToolTip("0 = infinito")

        self._inp_timeout = QSpinBox()
        self._inp_timeout.setRange(100, 30000)
        self._inp_timeout.setValue(2000)
        self._inp_timeout.setSuffix(" ms")
        self._inp_timeout.setFixedHeight(34)
        self._inp_timeout.setFixedWidth(95)

        self._inp_interval = QSpinBox()
        self._inp_interval.setRange(100, 60000)
        self._inp_interval.setValue(1000)
        self._inp_interval.setSuffix(" ms")
        self._inp_interval.setFixedHeight(34)
        self._inp_interval.setFixedWidth(95)

        grid.addWidget(self._inp_host, 1, 0)
        grid.addWidget(self._inp_port, 1, 1)
        grid.addWidget(self._cmb_mode, 1, 2)
        grid.addWidget(self._cmb_ip, 1, 3)
        grid.addWidget(self._inp_count, 1, 4)
        grid.addWidget(self._inp_timeout, 1, 5)
        grid.addWidget(self._inp_interval, 1, 6)

        # Botões Ping / Parar
        self._btn_ping = QPushButton("⚡  Ping")
        self._btn_ping.setFixedHeight(34)
        self._btn_ping.setFixedWidth(110)
        self._btn_ping.setStyleSheet(_PRIMARY_BTN)
        self._btn_ping.clicked.connect(self._on_ping_clicked)

        self._btn_stop = QPushButton("⏹  Parar")
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setFixedWidth(100)
        self._btn_stop.setStyleSheet(_STOP_BTN)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)

        grid.addWidget(self._btn_ping, 1, 7)
        grid.addWidget(self._btn_stop, 1, 8)

        panel_layout.addLayout(grid)
        root.addWidget(panel)
        root.addSpacing(10)

        # ── Splitter principal: gráfico+stats | console ─────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: palette(mid);
                border-radius: 2px;
                margin: 2px 80px;
            }
        """)

        # ── Seção superior: gráfico + stats ─────────────────────────
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        # Gráfico RTT grande
        graph_frame = QFrame()
        graph_frame.setObjectName("QPGraphFrame")
        graph_frame.setStyleSheet("""
            #QPGraphFrame {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        graph_inner = QVBoxLayout(graph_frame)
        graph_inner.setContentsMargins(10, 8, 10, 8)
        graph_inner.setSpacing(4)

        graph_title = QLabel("RTT em Tempo Real")
        graph_title.setStyleSheet(
            "color:palette(text); font-size:11px; font-weight:bold; letter-spacing:0.5px;"
        )
        graph_inner.addWidget(graph_title)

        self._graph = RttGraph()
        self._graph.MAX_POINTS = 120
        self._graph.reset()
        self._graph.setMinimumHeight(140)
        self._graph.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        graph_inner.addWidget(self._graph, 1)

        top_layout.addWidget(graph_frame, 7)

        # Painel de estatísticas
        stats_frame = QFrame()
        stats_frame.setObjectName("QPStatsFrame")
        stats_frame.setStyleSheet("""
            #QPStatsFrame {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        stats_inner = QVBoxLayout(stats_frame)
        stats_inner.setContentsMargins(14, 10, 14, 10)
        stats_inner.setSpacing(6)

        stats_title = QLabel("Estatísticas")
        stats_title.setStyleSheet(
            "color:palette(text); font-size:11px; font-weight:bold; letter-spacing:0.5px;"
        )
        stats_inner.addWidget(stats_title)
        stats_inner.addWidget(_hline())

        # Indicador de status
        status_row = QHBoxLayout()
        self._lbl_status_dot = QLabel("●")
        self._lbl_status_dot.setStyleSheet("color:#6b7280; font-size:18px;")
        self._lbl_status_dot.setFixedWidth(24)
        self._lbl_status = QLabel("INATIVO")
        self._lbl_status.setStyleSheet("color:#6b7280; font-size:12px; font-weight:bold;")
        status_row.addWidget(self._lbl_status_dot)
        status_row.addWidget(self._lbl_status, 1)
        stats_inner.addLayout(status_row)

        # IP resolvido
        self._lbl_resolved = QLabel("—")
        self._lbl_resolved.setStyleSheet("color:#6b7280; font-size:10px;")
        self._lbl_resolved.setWordWrap(True)
        stats_inner.addWidget(self._lbl_resolved)
        stats_inner.addWidget(_hline())

        # Stats grid
        self._val_rtt = _stat_value()
        self._val_avg = _stat_value()
        self._val_min = _stat_value()
        self._val_max = _stat_value()
        self._val_loss = _stat_value("0%")
        self._val_jitter = _stat_value()
        self._val_seq = _stat_value("0")
        self._val_elapsed = _stat_value()

        stat_pairs = [
            ("RTT ATUAL", self._val_rtt),
            ("MÉDIA", self._val_avg),
            ("MÍNIMO", self._val_min),
            ("MÁXIMO", self._val_max),
            ("PERDA %", self._val_loss),
            ("JITTER", self._val_jitter),
            ("SEQ", self._val_seq),
            ("DURAÇÃO", self._val_elapsed),
        ]
        for label_text, widget in stat_pairs:
            row = QHBoxLayout()
            row.setSpacing(4)
            lbl = QLabel(label_text)
            lbl.setStyleSheet(_STAT_LABEL_STYLE)
            lbl.setFixedWidth(70)
            row.addWidget(lbl)
            row.addWidget(widget, 1)
            stats_inner.addLayout(row)

        stats_inner.addStretch()

        stats_frame.setFixedWidth(240)
        top_layout.addWidget(stats_frame, 3)

        splitter.addWidget(top_widget)

        # ── Seção inferior: console ─────────────────────────────────
        console_frame = QFrame()
        console_frame.setObjectName("QPConsoleFrame")
        console_frame.setStyleSheet("""
            #QPConsoleFrame {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(10, 8, 10, 8)
        console_layout.setSpacing(4)

        # Toolbar do console
        console_toolbar = QHBoxLayout()
        console_toolbar.setSpacing(6)

        console_title = QLabel("Console")
        console_title.setStyleSheet(
            "color:palette(text); font-size:11px; font-weight:bold; letter-spacing:0.5px;"
        )
        console_toolbar.addWidget(console_title)
        console_toolbar.addStretch()

        for text, slot in [
            ("🗑 Limpar", self._clear_console),
            ("📋 Copiar", self._copy_console),
            ("💾 CSV", self._export_csv),
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(24)
            btn.setStyleSheet(_TOOLBAR_BTN)
            btn.clicked.connect(slot)
            console_toolbar.addWidget(btn)

        console_layout.addLayout(console_toolbar)

        self._console = QPlainTextEdit()
        self._console.setReadOnly(True)
        self._console.setMaximumBlockCount(self.MAX_CONSOLE_LINES)
        self._console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._apply_console_theme()
        console_layout.addWidget(self._console, 1)

        splitter.addWidget(console_frame)

        # Proporções iniciais do splitter (60% gráfico, 40% console)
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        root.addWidget(splitter, 1)

        # Placeholder quando vazio
        self._placeholder = QLabel(
            "⚡ Ping Rápido\n\n"
            "Digite um host e pressione Enter ou clique em ⚡ Ping\n"
            "para iniciar um diagnóstico rápido."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            "color:#45475a; font-size:14px; line-height:1.8;"
        )
        # O placeholder fica escondido quando houver conteúdo
        self._placeholder.setVisible(False)

        # Timer para atualizar duração
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)

    # ------------------------------------------------------------------
    # Controle
    # ------------------------------------------------------------------

    def _on_ping_clicked(self):
        host = self._inp_host.text().strip()
        if not host:
            self._inp_host.setFocus()
            return
        # Para teste anterior se rodando
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(500)
        self._start_ping(host)

    def _start_ping(self, host: str):
        self._reset_state()
        self._set_status("INICIANDO…", "#a78bfa")
        self._btn_ping.setEnabled(False)
        self._btn_stop.setEnabled(True)

        self._log_info(f"Iniciando ping para {host}...")

        cfg = ProbeConfig(
            host=host,
            port=self._inp_port.value(),
            mode=self._cmb_mode.currentData(),
            ip_version=self._cmb_ip.currentData(),
            count=self._inp_count.value(),
            timeout_ms=self._inp_timeout.value(),
            interval_ms=self._inp_interval.value(),
        )

        self._start_time = time.monotonic()
        self._elapsed_timer.start()

        self._worker = PingWorker(cfg)
        self._worker.result.connect(self._on_result)
        self._worker.resolved.connect(self._on_resolved)
        self._worker.error.connect(self._on_error)
        self._worker.stats.connect(self._on_finished)
        self._worker.start()

    def _stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._log_info("Ping interrompido pelo usuário.")
        self._elapsed_timer.stop()
        self._set_status("PARADO", "#6b7280")
        self._btn_ping.setEnabled(True)
        self._btn_stop.setEnabled(False)

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
        self._graph.reset()
        self._reset_stats_display()

    def _reset_stats_display(self):
        for w in (self._val_rtt, self._val_avg, self._val_min,
                  self._val_max, self._val_jitter, self._val_elapsed):
            w.setText("—")
            w.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")
        self._val_loss.setText("0%")
        self._val_loss.setStyleSheet("color:#4ade80; font-size:18px; font-weight:bold;")
        self._val_seq.setText("0")
        self._val_seq.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")
        self._lbl_resolved.setText("—")

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_resolved(self, ip: str, version: str):
        self._resolved_ip = ip
        self._resolved_ver = version
        self._lbl_resolved.setText(f"{ip}  [{version}]")
        self._log_info(f"Resolvido: {ip} [{version}]")

    def _on_result(self, r: PingResult):
        self._results.append(r)
        timeout = not r.success or r.elapsed_ms <= 0
        self._graph.add_point(r.elapsed_ms if not timeout else 0.0, timeout)

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
        if r.success:
            self._set_status("ONLINE", "#4ade80")
        else:
            self._set_status("TIMEOUT", "#f87171")

        # RTT atual
        if r.success:
            c = _rtt_color(r.elapsed_ms)
            self._val_rtt.setText(f"{r.elapsed_ms:.1f} ms")
            self._val_rtt.setStyleSheet(f"color:{c}; font-size:18px; font-weight:bold;")
        else:
            self._val_rtt.setText("timeout")
            self._val_rtt.setStyleSheet("color:#f87171; font-size:16px; font-weight:bold;")

        # Estatísticas
        self._update_stats()

        # Seq
        self._val_seq.setText(str(r.seq))
        self._val_seq.setStyleSheet("color:palette(text); font-size:18px; font-weight:bold;")

        # Console log
        self._log_result(r)

    def _on_error(self, msg: str):
        self._set_status("ERRO", "#facc15")
        self._log_error(msg)
        self._btn_ping.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._elapsed_timer.stop()

    def _on_finished(self, stats: dict):
        self._elapsed_timer.stop()
        self._update_elapsed()
        self._btn_ping.setEnabled(True)
        self._btn_stop.setEnabled(False)

        total = self._total_count
        ok = self._ok_count
        lost = total - ok
        self._log_info(
            f"Concluído: {total} enviados, {ok} recebidos, "
            f"{lost} perdidos ({lost/total*100:.1f}% perda)"
            if total > 0 else "Concluído: nenhum pacote enviado."
        )

        if total > 0 and self._ok_count > 0:
            self._set_status("CONCLUÍDO", "#4ade80")
        elif total > 0:
            self._set_status("CONCLUÍDO", "#f87171")
        else:
            self._set_status("CONCLUÍDO", "#6b7280")

    def _on_mode_changed(self):
        is_icmp = self._cmb_mode.currentData() == ProbeMode.ICMP
        self._inp_port.setEnabled(not is_icmp)
        self._inp_port.setToolTip("ICMP não usa porta" if is_icmp else "")

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
            avg_c = _rtt_color(avg)
            self._val_avg.setText(f"{avg:.1f} ms")
            self._val_avg.setStyleSheet(f"color:{avg_c}; font-size:18px; font-weight:bold;")
        else:
            self._val_avg.setText("—")
            self._val_avg.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")

        # Min
        if ok:
            self._val_min.setText(f"{mn:.1f} ms")
            self._val_min.setStyleSheet(
                f"color:{_rtt_color(mn)}; font-size:18px; font-weight:bold;"
            )
        else:
            self._val_min.setText("—")
            self._val_min.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")

        # Max
        if ok:
            self._val_max.setText(f"{mx:.1f} ms")
            self._val_max.setStyleSheet(
                f"color:{_rtt_color(mx)}; font-size:18px; font-weight:bold;"
            )
        else:
            self._val_max.setText("—")
            self._val_max.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")

        # Loss
        loss_c = "#f87171" if loss_pct > 5 else ("#facc15" if loss_pct > 0 else "#4ade80")
        self._val_loss.setText(f"{loss_pct:.1f}%")
        self._val_loss.setStyleSheet(f"color:{loss_c}; font-size:18px; font-weight:bold;")

        # Jitter
        if ok:
            jit_c = _rtt_color(jitter * 2)  # jitter tends to be smaller, scale for color
            self._val_jitter.setText(f"{jitter:.1f} ms")
            self._val_jitter.setStyleSheet(
                f"color:{jit_c}; font-size:18px; font-weight:bold;"
            )
        else:
            self._val_jitter.setText("—")
            self._val_jitter.setStyleSheet("color:#6b7280; font-size:18px; font-weight:bold;")

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
        self._val_elapsed.setText(txt)
        self._val_elapsed.setStyleSheet(
            "color:palette(text); font-size:18px; font-weight:bold;"
        )

    def _set_status(self, text: str, color: str):
        self._lbl_status_dot.setStyleSheet(f"color:{color}; font-size:18px;")
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet(
            f"color:{color}; font-size:12px; font-weight:bold;"
        )

    # ------------------------------------------------------------------
    # Console
    # ------------------------------------------------------------------

    def _log_result(self, r: PingResult):
        ts = datetime.now().strftime("%H:%M:%S")
        mode = self._cmb_mode.currentData().value
        port_info = f":{self._inp_port.value()}" if mode != "ICMP" else ""
        ip = self._resolved_ip or self._inp_host.text().strip()

        if r.success:
            line = (
                f"[{ts}]  ✅  Reply from {ip}{port_info}: "
                f"time={r.elapsed_ms:.1f}ms seq={r.seq} ({mode})"
            )
        else:
            note = f" — {r.note}" if r.note else ""
            line = f"[{ts}]  ❌  Request timeout seq={r.seq}{note}"

        self._console.appendPlainText(line)

    def _log_info(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._console.appendPlainText(f"[{ts}]  ℹ️  {msg}")

    def _log_error(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._console.appendPlainText(f"[{ts}]  ⚠️  ERRO: {msg}")

    def _clear_console(self):
        self._console.clear()

    def _copy_console(self):
        text = self._console.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _export_csv(self):
        if not self._results:
            return
        host = self._inp_host.text().strip().replace(":", "_").replace("/", "_")
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

    def _apply_console_theme(self):
        app = QApplication.instance()
        dark = True
        if app:
            win_color = app.palette().color(app.palette().ColorRole.Window)
            dark = win_color.lightness() < 128
        self._console.setStyleSheet(
            _CONSOLE_STYLE_DARK if dark else _CONSOLE_STYLE_LIGHT
        )

    def apply_theme(self, dark: bool):
        """Called by MainWindow when theme changes."""
        self._console.setStyleSheet(
            _CONSOLE_STYLE_DARK if dark else _CONSOLE_STYLE_LIGHT
        )
        self._graph.apply_theme(dark)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup(self):
        """Stop worker for shutdown."""
        self._elapsed_timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(500)
