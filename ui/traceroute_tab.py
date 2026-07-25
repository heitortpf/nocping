"""
NOCPing — ui/traceroute_tab.py
Aba de Traceroute ICMP em tempo real.

Redesenhada para usar o design system (ui/theme/): card de controle com
primary_button()/secondary_button(), tabela de hops com zebra striping sutil
e cores por token, e um aviso visual quando o processo não tem privilégio de
Administrador (traceroute exige raw socket ICMP — core/network.py não foi
alterado, só a camada visual).
"""
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QFileDialog,
)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import pyqtSignal

from core.models import IPVersion
from core.network import is_admin
from core.workers import TracerouteWorker
from .widgets._utils import field_label as _lbl, rtt_color as _rtt_color, TABLE_STYLE
from .widgets._worker_tab import WorkerTabMixin
from .theme.tokens import DARK, SPACING, RADIUS
from .theme.components import card_frame, primary_button, secondary_button, admin_warning


class TracerouteTab(WorkerTabMixin, QWidget):
    traceroute_finished = pyqtSignal(str, int, bool)
    _WORKER_WAIT_GUARDED = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: TracerouteWorker | None = None
        self._manually_stopped = False
        self._row_map: dict[int, int] = {}  # ttl -> linha da tabela
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        root.setSpacing(SPACING.md)

        # ── Card de controle ──────────────────────────────────────────
        panel = card_frame(RADIUS.md)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        pl.setSpacing(SPACING.sm)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING.sm)
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

        self._btn_start = primary_button("Rastrear", icon="▶")
        self._btn_start.setFixedHeight(34)
        self._btn_start.clicked.connect(self._start)

        self._btn_stop = secondary_button("Parar", icon="⏹")
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)

        grid.addWidget(self._inp_host,   1, 0)
        grid.addWidget(self._cmb_ip,     1, 1)
        grid.addWidget(self._spn_hops,   1, 2)
        grid.addWidget(self._spn_timeout, 1, 3)
        grid.addWidget(self._btn_start,  1, 4)
        grid.addWidget(self._btn_stop,   1, 5)
        pl.addLayout(grid)

        # Aviso de privilégio insuficiente — traceroute exige raw socket ICMP
        if not is_admin():
            pl.addWidget(admin_warning(
                "Sem privilégios de Administrador — traceroute (raw socket ICMP) não vai funcionar."
            ))

        root.addWidget(panel)

        # ── Status + ações ──────────────────────────────────────────────
        self._lbl_status = QLabel("Digite um host e clique em Rastrear.")
        self._lbl_status.setStyleSheet(f"color:{DARK.text_muted}; font-size:12px; padding:2px 0;")

        self._btn_clear = secondary_button("Limpar", icon="🗑")
        self._btn_clear.setFixedHeight(26)
        self._btn_clear.clicked.connect(self._clear)

        self._btn_export = secondary_button("Exportar CSV", icon="💾")
        self._btn_export.setFixedHeight(26)
        self._btn_export.clicked.connect(self._export_csv)

        status_row = QHBoxLayout()
        status_row.setSpacing(SPACING.sm)
        status_row.addWidget(self._lbl_status, 1)
        status_row.addWidget(self._btn_clear)
        status_row.addWidget(self._btn_export)
        root.addLayout(status_row)

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
        self._table.setAlternatingRowColors(True)
        mono = QFont("Consolas, Courier New, monospace")
        mono.setPointSize(11)
        self._table.setFont(mono)
        self._table.setStyleSheet(
            TABLE_STYLE +
            "QTableWidget::item { padding:2px 4px; }"
            "QTableWidget { alternate-background-color:palette(alternate-base); }"
        )
        root.addWidget(self._table, 1)

    # ------------------------------------------------------------------

    def _worker_signal_pairs(self):
        return [
            ("hop",      "_on_hop"),
            ("error",    "_on_error"),
            ("finished", "_on_finished"),
        ]

    def _start(self):
        host = self._inp_host.text().strip()
        if not host:
            self._inp_host.setFocus()
            return

        self._cleanup_worker()
        self._table.setRowCount(0)
        self._row_map.clear()
        self._manually_stopped = False
        self._lbl_status.setText(f"Rastreando rota para  {host}…")
        self._lbl_status.setStyleSheet(f"color:{DARK.info}; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_clear.setEnabled(False)
        self._btn_export.setEnabled(False)

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
        self._manually_stopped = True
        if self._worker:
            self._worker.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_clear.setEnabled(True)
        self._btn_export.setEnabled(self._table.rowCount() > 0)
        self._lbl_status.setText("Rastreamento interrompido.")
        self._lbl_status.setStyleSheet(f"color:{DARK.text_muted}; font-size:12px; padding:2px 0;")

    def _on_hop(self, hop: dict):
        ttl = hop["ttl"]
        row = self._row_map.get(ttl)
        if row is None:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._row_map[ttl] = row

        from_ip = hop["from_ip"] or "* * *"
        ms = hop["elapsed_ms"]
        timed_out = hop["timeout"]
        reached = hop["destination_reached"]
        resolving = hop.get("hostname_pending", False)

        if timed_out:
            rtt_text = "* * *"
            rtt_color = DARK.text_muted
            ip_color  = DARK.text_muted
            note_text = "sem resposta"
            note_color = DARK.text_muted
        elif reached:
            rtt_text = f"{ms:.1f} ms"
            rtt_color = _rtt_color(ms)
            ip_color  = DARK.success
            note_text = "destino"
            note_color = DARK.success
        else:
            rtt_text = f"{ms:.1f} ms"
            rtt_color = _rtt_color(ms)
            ip_color  = None  # cor padrão da tabela (palette(text)) — sem semântica própria
            note_text = "router"
            note_color = DARK.text_muted

        if resolving:
            hostname_text = "resolvendo…"
            hostname_color = DARK.info
        else:
            hostname_text = hop.get("hostname") or "—"
            hostname_color = DARK.text_muted

        def cell(text: str, color: str | None) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            if color is not None:
                item.setForeground(QColor(color))
            return item

        self._table.setItem(row, 0, cell(str(ttl),   DARK.text_muted))
        self._table.setItem(row, 1, cell(from_ip,     ip_color))
        self._table.setItem(row, 2, cell(hostname_text, hostname_color))
        self._table.setItem(row, 3, cell(rtt_text,    rtt_color))
        self._table.setItem(row, 4, cell(note_text,   note_color))
        self._table.scrollToBottom()

    def _on_error(self, msg: str):
        self._lbl_status.setText(f"Erro: {msg}")
        self._lbl_status.setStyleSheet(f"color:{DARK.danger}; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_clear.setEnabled(True)
        self._btn_export.setEnabled(self._table.rowCount() > 0)

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
            self._lbl_status.setStyleSheet(f"color:{DARK.success}; font-size:12px; padding:2px 0;")
        else:
            self._lbl_status.setText(
                f"Rastreamento concluído — destino não alcançado em {total} hop(s)."
            )
            self._lbl_status.setStyleSheet(f"color:{DARK.warning}; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_clear.setEnabled(True)
        self._btn_export.setEnabled(total > 0)

        if not self._manually_stopped:
            host = self._inp_host.text().strip()
            self.traceroute_finished.emit(host, total, reached)

    def _clear(self):
        self._table.setRowCount(0)
        self._row_map.clear()
        self._btn_export.setEnabled(False)
        self._lbl_status.setText("Digite um host e clique em Rastrear.")
        self._lbl_status.setStyleSheet(f"color:{DARK.text_muted}; font-size:12px; padding:2px 0;")

    def _export_csv(self):
        if self._table.rowCount() == 0:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Traceroute CSV", "nocping_traceroute.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Hop", "IP", "Hostname", "RTT", "Notas"])
            for row in range(self._table.rowCount()):
                writer.writerow([
                    self._table.item(row, col).text() if self._table.item(row, col) else ""
                    for col in range(self._table.columnCount())
                ])
