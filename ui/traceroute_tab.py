"""
NOCPing — ui/traceroute_tab.py
Aba de Traceroute ICMP em tempo real.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from core.models import IPVersion
from core.workers import TracerouteWorker
from .widgets._utils import field_label as _lbl, rtt_color as _rtt_color, PRIMARY_BTN_STYLE, TABLE_STYLE


class TracerouteTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: TracerouteWorker | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # ── Painel de controles ─────────────────────────────────────────
        panel = QFrame()
        panel.setObjectName("TrCtrlPanel")
        panel.setStyleSheet("""
            #TrCtrlPanel {
                background: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(14, 10, 14, 10)
        pl.setSpacing(8)

        # Grid: linha 0 = rótulos, linha 1 = campos
        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)  # host — expansível

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("VERSÃO IP"), 0, 1)
        grid.addWidget(_lbl("MAX HOPS"), 0, 2)
        grid.addWidget(_lbl("TIMEOUT"),  0, 3)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("ex: 8.8.8.8 ou google.com")
        self._inp_host.setFixedHeight(34)
        self._inp_host.setMinimumWidth(120)
        self._inp_host.returnPressed.connect(self._start)

        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedHeight(34)
        self._cmb_ip.setFixedWidth(80)

        self._spn_hops = QSpinBox()
        self._spn_hops.setRange(1, 64)
        self._spn_hops.setValue(30)
        self._spn_hops.setFixedHeight(34)
        self._spn_hops.setFixedWidth(70)

        self._spn_timeout = QSpinBox()
        self._spn_timeout.setRange(500, 10000)
        self._spn_timeout.setValue(2000)
        self._spn_timeout.setSuffix(" ms")
        self._spn_timeout.setFixedHeight(34)
        self._spn_timeout.setFixedWidth(110)

        self._btn_start = QPushButton("▶  Rastrear")
        self._btn_start.setFixedHeight(34)
        self._btn_start.setStyleSheet(PRIMARY_BTN_STYLE)
        self._btn_start.clicked.connect(self._start)

        self._btn_stop = QPushButton("⏹  Parar")
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            "QPushButton{background:palette(button);color:palette(button-text);"
            "border-radius:6px;font-size:13px;border:none;padding:0 14px;}"
            "QPushButton:hover{background:palette(mid);}"
            "QPushButton:disabled{color:palette(placeholder-text);}"
        )
        self._btn_stop.clicked.connect(self._stop)

        grid.addWidget(self._inp_host,   1, 0)
        grid.addWidget(self._cmb_ip,     1, 1)
        grid.addWidget(self._spn_hops,   1, 2)
        grid.addWidget(self._spn_timeout, 1, 3)
        grid.addWidget(self._btn_start,  1, 4)
        grid.addWidget(self._btn_stop,   1, 5)
        pl.addLayout(grid)

        root.addWidget(panel)
        root.addSpacing(8)

        # ── Status ──────────────────────────────────────────────────────
        self._lbl_status = QLabel("Digite um host e clique em Rastrear.")
        self._lbl_status.setStyleSheet("color:#6b7280; font-size:12px; padding:2px 0;")
        root.addWidget(self._lbl_status)
        root.addSpacing(4)

        # ── Tabela de hops ──────────────────────────────────────────────
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Hop", "IP", "Hostname", "RTT", "Notas"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 50)
        self._table.setColumnWidth(1, 140)
        self._table.setColumnWidth(3, 100)
        self._table.setColumnWidth(4, 140)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        mono = QFont("Consolas, Courier New, monospace")
        mono.setPointSize(11)
        self._table.setFont(mono)
        self._table.setStyleSheet(
            TABLE_STYLE + "QTableWidget::item { padding:2px 4px; }"
        )
        root.addWidget(self._table, 1)

    # ------------------------------------------------------------------

    def _start(self):
        host = self._inp_host.text().strip()
        if not host:
            self._inp_host.setFocus()
            return

        self._table.setRowCount(0)
        self._lbl_status.setText(f"Rastreando rota para  {host}…")
        self._lbl_status.setStyleSheet("color:#a78bfa; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)

        self._worker = TracerouteWorker(
            host=host,
            ip_version=self._cmb_ip.currentData(),
            max_hops=self._spn_hops.value(),
            timeout_ms=self._spn_timeout.value(),
        )
        self._worker.hop.connect(self._on_hop)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _stop(self):
        if self._worker:
            self._worker.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._lbl_status.setText("Rastreamento interrompido.")
        self._lbl_status.setStyleSheet("color:#6b7280; font-size:12px; padding:2px 0;")

    def _on_hop(self, hop: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)

        ttl = hop["ttl"]
        from_ip = hop["from_ip"] or "* * *"
        hostname = hop.get("hostname") or "—"
        ms = hop["elapsed_ms"]
        timed_out = hop["timeout"]
        reached = hop["destination_reached"]

        if timed_out:
            rtt_text = "* * *"
            rtt_color = "#6b7280"
            ip_color  = "#6b7280"
            note_text = "sem resposta"
            note_color = "#6b7280"
        elif reached:
            rtt_text = f"{ms:.1f} ms"
            rtt_color = _rtt_color(ms)
            ip_color  = "#4ade80"
            note_text = "destino"
            note_color = "#4ade80"
        else:
            rtt_text = f"{ms:.1f} ms"
            rtt_color = _rtt_color(ms)
            ip_color  = "#cdd6f4"
            note_text = "router"
            note_color = "#9ca3af"

        def cell(text: str, color: str) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setForeground(QColor(color))
            return item

        self._table.setItem(row, 0, cell(str(ttl),   "#6b7280"))
        self._table.setItem(row, 1, cell(from_ip,     ip_color))
        self._table.setItem(row, 2, cell(hostname,    "#9ca3af"))
        self._table.setItem(row, 3, cell(rtt_text,    rtt_color))
        self._table.setItem(row, 4, cell(note_text,   note_color))
        self._table.scrollToBottom()

    def _on_error(self, msg: str):
        self._lbl_status.setText(f"Erro: {msg}")
        self._lbl_status.setStyleSheet("color:#f87171; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_finished(self):
        total = self._table.rowCount()
        reached = any(
            self._table.item(r, 4) and self._table.item(r, 4).text() == "destino"
            for r in range(total)
        )
        if reached:
            self._lbl_status.setText(
                f"Rota concluída — {total} hop(s) até o destino."
            )
            self._lbl_status.setStyleSheet("color:#4ade80; font-size:12px; padding:2px 0;")
        else:
            self._lbl_status.setText(
                f"Rastreamento concluído — destino não alcançado em {total} hop(s)."
            )
            self._lbl_status.setStyleSheet("color:#facc15; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)


