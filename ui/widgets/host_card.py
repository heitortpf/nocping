"""
NOCPing — ui/widgets/host_card.py
Card individual por host — layout com seções separadas e hierarquia visual clara.
"""
import csv

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.models import ProbeConfig, ProbeMode, IPVersion, HostStatus, PingResult
from core.workers import PingWorker
from core.history_store import HistoryStore
from .rtt_graph import RttGraph
from ._utils import rtt_color as _rtt_color


STATUS_COLOR = {
    HostStatus.IDLE:    "#6b7280",
    HostStatus.RUNNING: "#a78bfa",
    HostStatus.UP:      "#4ade80",
    HostStatus.DOWN:    "#f87171",
    HostStatus.ERROR:   "#facc15",
}

STATUS_LABEL = {
    HostStatus.IDLE:    "INATIVO",
    HostStatus.RUNNING: "INICIANDO…",
    HostStatus.UP:      "ONLINE",
    HostStatus.DOWN:    "OFFLINE",
    HostStatus.ERROR:   "ERRO",
}


def _stat_col(label: str, value_widget: QLabel) -> QVBoxLayout:
    """Coluna de estatística: rótulo pequeno em cima, valor grande embaixo."""
    col = QVBoxLayout()
    col.setSpacing(1)
    lbl = QLabel(label)
    lbl.setStyleSheet("color:#6b7280; font-size:10px; letter-spacing:0.5px;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    col.addWidget(lbl)
    col.addWidget(value_widget)
    return col


class HostCard(QFrame):
    removed        = pyqtSignal(object)
    status_changed = pyqtSignal(str, object, object)  # host, old, new

    def __init__(self, config: ProbeConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._worker: PingWorker | None = None
        self._status = HostStatus.IDLE
        self._results = []

        self.setFixedWidth(320)
        self.setObjectName("HostCard")
        self.setStyleSheet("""
            #HostCard {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 10px;
            }
        """)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Cabeçalho ───────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("CardHeader")
        header.setStyleSheet("""
            #CardHeader {
                background: palette(alternate-base);
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid palette(mid);
            }
        """)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(12, 10, 12, 10)
        h_layout.setSpacing(4)

        # Hostname + botão remover
        title_row = QHBoxLayout()
        self._indicator = QLabel("●")
        self._indicator.setStyleSheet(
            f"color:{STATUS_COLOR[HostStatus.IDLE]}; font-size:16px;"
        )
        self._indicator.setFixedWidth(20)

        self._lbl_host = QLabel(self.config.host)
        font_host = QFont()
        font_host.setPointSize(13)
        font_host.setBold(True)
        self._lbl_host.setFont(font_host)
        self._lbl_host.setStyleSheet("color:#cdd6f4;")

        self._lbl_status_text = QLabel(STATUS_LABEL[HostStatus.IDLE])
        self._lbl_status_text.setStyleSheet(
            f"color:{STATUS_COLOR[HostStatus.IDLE]}; font-size:10px; font-weight:bold;"
        )

        btn_remove = QPushButton("✕")
        btn_remove.setFixedSize(22, 22)
        btn_remove.setStyleSheet(
            "QPushButton{background:transparent;color:#6b7280;border:none;font-size:14px;}"
            "QPushButton:hover{color:#f87171;}"
        )
        btn_remove.clicked.connect(lambda: self.removed.emit(self))

        title_row.addWidget(self._indicator)
        title_row.addWidget(self._lbl_host, 1)
        title_row.addWidget(self._lbl_status_text)
        title_row.addSpacing(6)
        title_row.addWidget(btn_remove)
        h_layout.addLayout(title_row)

        # Modo + Porta + IP resolvido
        sub_row = QHBoxLayout()
        _mode_str = self.config.mode.value
        if self.config.mode != ProbeMode.ICMP:
            _mode_str += f"  ·  porta {self.config.port}"
        self._lbl_mode = QLabel(_mode_str)
        self._lbl_mode.setStyleSheet("color:#6b7280; font-size:11px;")
        self._lbl_ip = QLabel("resolvendo…")
        self._lbl_ip.setStyleSheet("color:#6b7280; font-size:11px;")
        self._lbl_ip.setAlignment(Qt.AlignmentFlag.AlignRight)
        sub_row.addWidget(self._lbl_mode)
        sub_row.addStretch()
        sub_row.addWidget(self._lbl_ip)
        h_layout.addLayout(sub_row)

        root.addWidget(header)

        # ── Corpo ────────────────────────────────────────────────────────
        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 10, 12, 10)
        body_layout.setSpacing(10)

        # Seletor IPv4 / IPv6
        ip_row = QHBoxLayout()
        ip_lbl = QLabel("VERSÃO IP:")
        ip_lbl.setStyleSheet("color:#6b7280; font-size:10px; letter-spacing:0.5px;")
        ip_row.addWidget(ip_lbl)
        ip_row.addSpacing(6)

        self._ip_group = QButtonGroup(self)
        self._ip_group.setExclusive(True)
        for label, version in [("Auto", IPVersion.AUTO),
                                ("IPv4", IPVersion.IPV4),
                                ("IPv6", IPVersion.IPV6)]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            btn.setFixedWidth(44)
            btn.setStyleSheet("""
                QPushButton {
                    background:palette(button); color:palette(button-text);
                    border-radius:4px; font-size:11px; border:none;
                }
                QPushButton:checked { background:#7c3aed; color:#fff; font-weight:bold; }
                QPushButton:hover:!checked { background:palette(mid); color:palette(text); }
            """)
            btn.setProperty("version", version)
            btn.clicked.connect(self._on_ip_version_changed)
            self._ip_group.addButton(btn)
            ip_row.addWidget(btn)
            if version == self.config.ip_version:
                btn.setChecked(True)
        ip_row.addStretch()
        body_layout.addLayout(ip_row)

        # Divisor
        body_layout.addWidget(_hline())

        # ── Estatísticas — 3 colunas ────────────────────────────────────
        self._val_rtt  = _big_value("—")
        self._val_avg  = _big_value("—")
        self._val_loss = _big_value("0%")

        stats_row = QHBoxLayout()
        stats_row.setSpacing(0)
        stats_row.addLayout(_stat_col("RTT ATUAL",   self._val_rtt))
        stats_row.addWidget(_vline())
        stats_row.addLayout(_stat_col("MÉDIA",       self._val_avg))
        stats_row.addWidget(_vline())
        stats_row.addLayout(_stat_col("PERDA",       self._val_loss))
        body_layout.addLayout(stats_row)

        # Min / Max / Seq em linha secundária
        secondary = QHBoxLayout()
        self._lbl_min  = _dim_label("Mín: —")
        self._lbl_max  = _dim_label("Máx: —")
        self._lbl_seq  = _dim_label("Seq: 0")
        for l in (self._lbl_min, self._lbl_max, self._lbl_seq):
            secondary.addWidget(l)
            if l is not self._lbl_seq:
                secondary.addStretch()
        body_layout.addLayout(secondary)

        # Divisor
        body_layout.addWidget(_hline())

        # Gráfico RTT
        self._graph = RttGraph()
        self._graph.setFixedHeight(80)
        body_layout.addWidget(self._graph)

        _link_style = (
            "QPushButton{color:#7c3aed;font-size:10px;border:none;background:transparent;}"
            "QPushButton:hover{color:#6d28d9;text-decoration:underline;}"
        )
        footer_row = QHBoxLayout()
        btn_history = QPushButton("⏱ Histórico")
        btn_history.setFlat(True)
        btn_history.setStyleSheet(_link_style)
        btn_history.clicked.connect(self._open_history)
        footer_row.addWidget(btn_history, alignment=Qt.AlignmentFlag.AlignLeft)

        btn_export_rtt = QPushButton("⬇ Exportar RTT")
        btn_export_rtt.setFlat(True)
        btn_export_rtt.setStyleSheet(_link_style)
        btn_export_rtt.clicked.connect(self._export_rtt)
        footer_row.addWidget(btn_export_rtt, alignment=Qt.AlignmentFlag.AlignRight)
        body_layout.addLayout(footer_row)

        # Divisor
        body_layout.addWidget(_hline())

        # Botões Start / Stop
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_start = QPushButton("▶  Iniciar")
        self._btn_stop  = QPushButton("⏹  Parar")
        self._btn_start.setFixedHeight(30)
        self._btn_stop.setFixedHeight(30)
        self._btn_start.setStyleSheet(
            "QPushButton{background:#7c3aed;color:#fff;border-radius:5px;"
            "font-size:12px;font-weight:bold;border:none;}"
            "QPushButton:hover{background:#6d28d9;}"
            "QPushButton:disabled{background:palette(button);color:palette(placeholder-text);}"
        )
        self._btn_stop.setStyleSheet(
            "QPushButton{background:palette(button);color:palette(button-text);"
            "border-radius:5px;font-size:12px;border:none;}"
            "QPushButton:hover{background:palette(mid);}"
            "QPushButton:disabled{color:palette(placeholder-text);}"
        )
        self._btn_stop.setEnabled(False)
        self._btn_start.clicked.connect(self.start)
        self._btn_stop.clicked.connect(self.stop)
        btn_row.addWidget(self._btn_start, 1)
        btn_row.addWidget(self._btn_stop, 1)
        body_layout.addLayout(btn_row)

        root.addWidget(body)

    # ------------------------------------------------------------------
    # Controle
    # ------------------------------------------------------------------

    def start(self):
        if self._worker and self._worker.isRunning():
            return
        self._results.clear()
        self._graph.reset()
        self._reset_stats()
        self._set_status(HostStatus.RUNNING)
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._lbl_ip.setText("resolvendo…")

        self._worker = PingWorker(self.config)
        self._worker.result.connect(self._on_result)
        self._worker.resolved.connect(self._on_resolved)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def stop(self):
        if self._worker:
            self._worker.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        if self._status == HostStatus.RUNNING:
            self._set_status(HostStatus.IDLE)

    def start_if_idle(self):
        if self._status == HostStatus.IDLE:
            self.start()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_resolved(self, ip: str, version: str):
        self._lbl_ip.setText(f"{ip}  [{version}]")

    def _on_result(self, r: PingResult):
        self._results.append(r)
        HistoryStore.instance().record(self.config.host, r)
        timeout = not r.success or r.elapsed_ms <= 0
        self._graph.add_point(r.elapsed_ms if not timeout else 0.0, timeout)

        if r.success:
            self._set_status(HostStatus.UP)
            c = _rtt_color(r.elapsed_ms)
            self._val_rtt.setText(f"{r.elapsed_ms:.1f} ms")
            self._val_rtt.setStyleSheet(f"color:{c}; font-size:20px; font-weight:bold;")
        else:
            self._set_status(HostStatus.DOWN)
            self._val_rtt.setText("timeout")
            self._val_rtt.setStyleSheet("color:#f87171; font-size:16px; font-weight:bold;")

        # Estatísticas acumuladas
        ok = [x for x in self._results if x.success and x.elapsed_ms > 0]
        lost = len(self._results) - len(ok)
        loss_pct = lost / len(self._results) * 100
        avg = sum(x.elapsed_ms for x in ok) / len(ok) if ok else 0.0
        mn  = min(x.elapsed_ms for x in ok) if ok else 0.0
        mx  = max(x.elapsed_ms for x in ok) if ok else 0.0

        avg_c = _rtt_color(avg) if ok else "#6b7280"
        self._val_avg.setText(f"{avg:.1f} ms" if ok else "—")
        self._val_avg.setStyleSheet(f"color:{avg_c}; font-size:20px; font-weight:bold;")

        loss_c = "#f87171" if loss_pct > 5 else ("#facc15" if loss_pct > 0 else "#4ade80")
        self._val_loss.setText(f"{loss_pct:.0f}%")
        self._val_loss.setStyleSheet(f"color:{loss_c}; font-size:20px; font-weight:bold;")

        self._lbl_min.setText(f"Mín: {mn:.1f}ms" if ok else "Mín: —")
        self._lbl_max.setText(f"Máx: {mx:.1f}ms" if ok else "Máx: —")
        self._lbl_seq.setText(f"Seq: {r.seq}")

    def _on_error(self, msg: str):
        self._set_status(HostStatus.ERROR)
        self._lbl_ip.setText(f"⚠  {msg[:36]}")
        self._val_rtt.setText("—")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_finished(self, _stats: dict):
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_ip_version_changed(self):
        for btn in self._ip_group.buttons():
            if btn.isChecked():
                self.config.ip_version = btn.property("version")
                if self._worker and self._worker.isRunning():
                    self._worker.stop()
                    self._worker.wait(400)
                    self.start()
                break

    def _open_history(self):
        from ui.widgets.history_dialog import HistoryDialog
        dlg = HistoryDialog(self.config.host, self)
        dlg.exec()

    def _export_rtt(self):
        if not self._results:
            return
        safe_host = self.config.host.replace(":", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar histórico RTT",
            f"rtt_{safe_host}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Seq", "Sucesso", "RTT (ms)", "Nota"])
            for r in self._results:
                writer.writerow([r.seq, r.success, f"{r.elapsed_ms:.3f}", r.note])

    def _set_status(self, status: HostStatus):
        old = self._status
        self._status = status
        c = STATUS_COLOR[status]
        self._indicator.setStyleSheet(f"color:{c}; font-size:16px;")
        self._lbl_status_text.setText(STATUS_LABEL[status])
        self._lbl_status_text.setStyleSheet(
            f"color:{c}; font-size:10px; font-weight:bold;"
        )
        if old != status and status in (HostStatus.UP, HostStatus.DOWN, HostStatus.ERROR):
            self.status_changed.emit(self.config.host, old, status)

    def _reset_stats(self):
        for w in (self._val_rtt, self._val_avg, self._val_loss):
            w.setText("—")
            w.setStyleSheet("color:#6b7280; font-size:20px; font-weight:bold;")
        self._val_loss.setText("0%")
        self._lbl_min.setText("Mín: —")
        self._lbl_max.setText("Máx: —")
        self._lbl_seq.setText("Seq: 0")

    @property
    def status(self) -> HostStatus:
        return self._status


# ---------------------------------------------------------------------------
# Helpers de widgets
# ---------------------------------------------------------------------------

def _big_value(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#6b7280; font-size:20px; font-weight:bold;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _dim_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#6b7280; font-size:10px;")
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:palette(mid); margin:0;")
    f.setFixedHeight(1)
    return f


def _vline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet("color:palette(mid);")
    f.setFixedWidth(1)
    f.setContentsMargins(0, 4, 0, 4)
    return f
