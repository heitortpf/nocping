"""
NOCPing — ui/mtr_tab.py
Aba MTR (My TraceRoute): traceroute contínuo com estatísticas por hop.
"""
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QFrame, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.models import IPVersion
from core.workers import MTRWorker
from .widgets._utils import field_label as _lbl, rtt_color as _rtt_color, PRIMARY_BTN_STYLE, TABLE_STYLE

_COL_HOP      = 0
_COL_IP       = 1
_COL_HOSTNAME = 2
_COL_LOSS     = 3
_COL_SENT     = 4
_COL_LAST     = 5
_COL_AVG      = 6
_COL_BEST     = 7
_COL_WORST    = 8
_COL_STDEV    = 9


def _loss_color(pct: float) -> str:
    if pct == 0:
        return "#4ade80"
    if pct < 5:
        return "#a3e635"
    if pct < 20:
        return "#facc15"
    return "#f87171"


class MTRTab(QWidget):
    mtr_finished = pyqtSignal(str, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: MTRWorker | None = None
        self._row_map: dict[int, int] = {}  # ttl -> row index
        self._manually_stopped = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(0)

        # ── Painel de controles ─────────────────────────────────────────
        panel = QFrame()
        panel.setObjectName("MTRCtrlPanel")
        panel.setStyleSheet("""
            #MTRCtrlPanel {
                background: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(14, 10, 14, 10)
        pl.setSpacing(8)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)

        grid.addWidget(_lbl("HOST / IP"),    0, 0)
        grid.addWidget(_lbl("VERSÃO IP"),    0, 1)
        grid.addWidget(_lbl("MAX HOPS"),     0, 2)
        grid.addWidget(_lbl("TIMEOUT"),      0, 3)
        grid.addWidget(_lbl("INTERVALO"),    0, 4)

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
        self._spn_timeout.setValue(1000)
        self._spn_timeout.setSuffix(" ms")
        self._spn_timeout.setFixedHeight(34)
        self._spn_timeout.setFixedWidth(110)

        self._spn_interval = QSpinBox()
        self._spn_interval.setRange(100, 5000)
        self._spn_interval.setValue(200)
        self._spn_interval.setSuffix(" ms")
        self._spn_interval.setFixedHeight(34)
        self._spn_interval.setFixedWidth(110)

        self._btn_start = QPushButton("▶  Iniciar MTR")
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

        grid.addWidget(self._inp_host,     1, 0)
        grid.addWidget(self._cmb_ip,       1, 1)
        grid.addWidget(self._spn_hops,     1, 2)
        grid.addWidget(self._spn_timeout,  1, 3)
        grid.addWidget(self._spn_interval, 1, 4)
        grid.addWidget(self._btn_start,    1, 5)
        grid.addWidget(self._btn_stop,     1, 6)
        pl.addLayout(grid)

        root.addWidget(panel)
        root.addSpacing(8)

        # ── Status + ações ──────────────────────────────────────────────
        self._lbl_status = QLabel("Digite um host e clique em Iniciar MTR.")
        self._lbl_status.setStyleSheet("color:#6b7280; font-size:12px; padding:2px 0;")

        _sec = (
            "QPushButton{background:palette(button);color:palette(button-text);"
            "border-radius:5px;font-size:12px;border:none;padding:0 10px;}"
            "QPushButton:hover{background:palette(mid);}"
            "QPushButton:disabled{color:palette(placeholder-text);}"
        )
        self._btn_clear = QPushButton("🗑  Limpar")
        self._btn_clear.setFixedHeight(26)
        self._btn_clear.setStyleSheet(_sec)
        self._btn_clear.clicked.connect(self._clear)

        self._btn_export = QPushButton("💾  Exportar CSV")
        self._btn_export.setFixedHeight(26)
        self._btn_export.setStyleSheet(_sec)
        self._btn_export.clicked.connect(self._export_csv)

        status_row = QHBoxLayout()
        status_row.addWidget(self._lbl_status, 1)
        status_row.addWidget(self._btn_clear)
        status_row.addWidget(self._btn_export)
        root.addLayout(status_row)
        root.addSpacing(4)

        # ── Tabela ──────────────────────────────────────────────────────
        headers = ["Hop", "IP", "Hostname", "Loss%", "Sent",
                   "Last", "Avg", "Best", "Worst", "StDev"]
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        hdr = self._table.horizontalHeader()
        for col, mode in [
            (_COL_HOP,      QHeaderView.ResizeMode.Fixed),
            (_COL_IP,       QHeaderView.ResizeMode.Fixed),
            (_COL_HOSTNAME, QHeaderView.ResizeMode.Stretch),
            (_COL_LOSS,     QHeaderView.ResizeMode.Fixed),
            (_COL_SENT,     QHeaderView.ResizeMode.Fixed),
            (_COL_LAST,     QHeaderView.ResizeMode.Fixed),
            (_COL_AVG,      QHeaderView.ResizeMode.Fixed),
            (_COL_BEST,     QHeaderView.ResizeMode.Fixed),
            (_COL_WORST,    QHeaderView.ResizeMode.Fixed),
            (_COL_STDEV,    QHeaderView.ResizeMode.Fixed),
        ]:
            hdr.setSectionResizeMode(col, mode)
        self._table.setColumnWidth(_COL_HOP,   46)
        self._table.setColumnWidth(_COL_IP,    150)
        self._table.setColumnWidth(_COL_LOSS,   70)
        self._table.setColumnWidth(_COL_SENT,   60)
        self._table.setColumnWidth(_COL_LAST,   80)
        self._table.setColumnWidth(_COL_AVG,    80)
        self._table.setColumnWidth(_COL_BEST,   80)
        self._table.setColumnWidth(_COL_WORST,  80)
        self._table.setColumnWidth(_COL_STDEV,  80)
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

    def _cleanup_worker(self):
        if self._worker is None:
            return
        try:
            self._worker.hop_discovered.disconnect(self._on_hop_discovered)
            self._worker.hop_update.disconnect(self._on_hop_update)
            self._worker.error.disconnect(self._on_error)
            self._worker.finished.disconnect(self._on_finished)
        except RuntimeError:
            pass
        self._worker.stop()
        self._worker.wait(2000)
        self._worker.deleteLater()
        self._worker = None

    def _start(self):
        host = self._inp_host.text().strip()
        if not host:
            self._inp_host.setFocus()
            return

        self._cleanup_worker()
        self._table.setRowCount(0)
        self._row_map.clear()
        self._manually_stopped = False
        self._lbl_status.setText(f"Rastreando MTR para  {host}…")
        self._lbl_status.setStyleSheet("color:#a78bfa; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_clear.setEnabled(False)
        self._btn_export.setEnabled(False)

        self._worker = MTRWorker(
            host=host,
            ip_version=self._cmb_ip.currentData(),
            max_hops=self._spn_hops.value(),
            timeout_ms=self._spn_timeout.value(),
            interval_ms=self._spn_interval.value(),
        )
        self._worker.hop_discovered.connect(self._on_hop_discovered)
        self._worker.hop_update.connect(self._on_hop_update)
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
        self._lbl_status.setText("MTR interrompido.")
        self._lbl_status.setStyleSheet("color:#6b7280; font-size:12px; padding:2px 0;")

    def _on_hop_discovered(self, ttl: int, ip: str, hostname: str):
        if ttl in self._row_map:
            row = self._row_map[ttl]
            self._set_cell(row, _COL_IP,       ip or "* * *", "#6b7280" if not ip else "#cdd6f4")
            self._set_cell(row, _COL_HOSTNAME, hostname or "—", "#9ca3af")
            return
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_map[ttl] = row
        self._set_cell(row, _COL_HOP,      str(ttl),       "#6b7280")
        self._set_cell(row, _COL_IP,       ip or "* * *",  "#6b7280" if not ip else "#cdd6f4")
        self._set_cell(row, _COL_HOSTNAME, hostname or "—","#9ca3af")
        for col in (_COL_LOSS, _COL_SENT, _COL_LAST, _COL_AVG,
                    _COL_BEST, _COL_WORST, _COL_STDEV):
            self._set_cell(row, col, "—", "#6b7280")

    def _on_hop_update(self, ttl: int, stats: dict):
        row = self._row_map.get(ttl)
        if row is None:
            return
        loss = stats["loss_pct"]
        self._set_cell(row, _COL_LOSS,  f"{loss:.1f}%",              _loss_color(loss))
        self._set_cell(row, _COL_SENT,  str(stats["sent"]),           "#9ca3af")
        self._set_cell(row, _COL_LAST,  self._fmt(stats["last_ms"]),  _rtt_color(stats["last_ms"]))
        self._set_cell(row, _COL_AVG,   self._fmt(stats["avg_ms"]),   _rtt_color(stats["avg_ms"]))
        self._set_cell(row, _COL_BEST,  self._fmt(stats["best_ms"]),  "#4ade80")
        self._set_cell(row, _COL_WORST, self._fmt(stats["worst_ms"]), _rtt_color(stats["worst_ms"]))
        self._set_cell(row, _COL_STDEV, self._fmt(stats["stdev_ms"]), "#9ca3af")

        hops = self._table.rowCount()
        sent = stats["sent"]
        self._lbl_status.setText(
            f"MTR ativo — {hops} hop(s) descobertos — {sent} sondas enviadas."
        )

    def _on_error(self, msg: str):
        self._lbl_status.setText(f"Erro: {msg}")
        self._lbl_status.setStyleSheet("color:#f87171; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_clear.setEnabled(True)
        self._btn_export.setEnabled(self._table.rowCount() > 0)

    def _on_finished(self):
        self._lbl_status.setText("MTR concluído.")
        self._lbl_status.setStyleSheet("color:#4ade80; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_clear.setEnabled(True)
        self._btn_export.setEnabled(self._table.rowCount() > 0)
        
        if not self._manually_stopped:
            host = self._inp_host.text().strip()
            self.mtr_finished.emit(host, self._table.rowCount())

    def _clear(self):
        self._table.setRowCount(0)
        self._row_map.clear()
        self._btn_export.setEnabled(False)
        self._lbl_status.setText("Digite um host e clique em Iniciar MTR.")
        self._lbl_status.setStyleSheet("color:#6b7280; font-size:12px; padding:2px 0;")

    def _export_csv(self):
        if self._table.rowCount() == 0:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar MTR CSV", "nocping_mtr.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Hop", "IP", "Hostname", "Loss%", "Sent",
                             "Last", "Avg", "Best", "Worst", "StDev"])
            for row in range(self._table.rowCount()):
                writer.writerow([
                    self._table.item(row, col).text() if self._table.item(row, col) else ""
                    for col in range(self._table.columnCount())
                ])

    # ------------------------------------------------------------------

    @staticmethod
    def _fmt(ms: float) -> str:
        return f"{ms:.1f} ms" if ms > 0 else "—"

    def _set_cell(self, row: int, col: int, text: str, color: str):
        item = self._table.item(row, col)
        if item is None:
            item = QTableWidgetItem(text)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                if col >= _COL_LOSS else
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            self._table.setItem(row, col, item)
        else:
            item.setText(text)
        item.setForeground(QColor(color))
