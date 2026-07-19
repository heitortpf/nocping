"""
NOCPing — ui/widgets/history_dialog.py
Diálogo de histórico persistente de RTT por host.
"""
import csv
import datetime

import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.history_store import HistoryStore
from ._utils import rtt_color as _rtt_color, TABLE_STYLE

_LIMITS = [("Últimos 100", 100), ("Últimos 500", 500),
           ("Últimos 1 000", 1000), ("Tudo", 0)]


class _HistoryLoadWorker(QThread):
    """Executa HistoryStore.query() fora da thread da GUI.

    query() aguarda a fila de escrita assíncrona esvaziar (flush); sob carga
    concorrente (várias abas gravando RTT ao mesmo tempo) isso pode demorar,
    então não pode rodar na thread principal sem travar a janela.
    """
    loaded = pyqtSignal(list)

    def __init__(self, host: str, limit: int, parent=None):
        super().__init__(parent)
        self._host = host
        self._limit = limit

    def run(self):
        rows = HistoryStore.instance().query(self._host, self._limit)
        self.loaded.emit(rows)


class HistoryDialog(QDialog):
    def __init__(self, host: str, parent=None):
        super().__init__(parent)
        self._host = host
        self._load_worker: "_HistoryLoadWorker | None" = None
        self.setWindowTitle(f"Histórico RTT — {host}")
        self.resize(860, 560)
        self.setMinimumSize(600, 400)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # ── Toolbar ─────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel(f"<b>{self._host}</b>"))
        toolbar.addStretch()

        toolbar.addWidget(QLabel("Exibir:"))
        self._cmb_limit = QComboBox()
        self._cmb_limit.setFixedHeight(28)
        for label, _ in _LIMITS:
            self._cmb_limit.addItem(label)
        self._cmb_limit.setCurrentIndex(1)
        self._cmb_limit.currentIndexChanged.connect(self._load)
        toolbar.addWidget(self._cmb_limit)

        _sec = (
            "QPushButton{background:palette(button);color:palette(button-text);"
            "border-radius:5px;font-size:12px;border:none;padding:0 12px;height:28px;}"
            "QPushButton:hover{background:palette(mid);}"
        )
        btn_export = QPushButton("⬇ Exportar CSV")
        btn_export.setStyleSheet(_sec)
        btn_export.clicked.connect(self._export_csv)
        toolbar.addWidget(btn_export)

        btn_clear = QPushButton("🗑 Limpar histórico")
        btn_clear.setStyleSheet(
            "QPushButton{background:#dc2626;color:#fff;border-radius:5px;"
            "font-size:12px;border:none;padding:0 12px;height:28px;}"
            "QPushButton:hover{background:#b91c1c;}"
        )
        btn_clear.clicked.connect(self._clear)
        toolbar.addWidget(btn_clear)

        root.addLayout(toolbar)

        # ── Gráfico ──────────────────────────────────────────────────────
        date_axis = pg.DateAxisItem(orientation='bottom')
        self._plot = pg.PlotWidget(axisItems={'bottom': date_axis})
        self._plot.setFixedHeight(160)
        self._plot.setBackground("#1e1e2e")
        self._plot.showAxis("left")
        self._plot.getAxis("left").setTextPen(pg.mkPen("#888"))
        self._plot.getAxis("bottom").setTextPen(pg.mkPen("#888"))
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.setMenuEnabled(False)
        self._plot.showGrid(y=True, alpha=0.15)
        self._curve = self._plot.plot(pen=pg.mkPen("#4ade80", width=1.5),
                                      fillLevel=0, brush=pg.mkBrush("#4ade8018"))
        root.addWidget(self._plot)

        # ── Tabela ───────────────────────────────────────────────────────
        headers = ["Timestamp", "Status", "RTT (ms)", "Nota"]
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 170)
        self._table.setColumnWidth(1, 80)
        self._table.setColumnWidth(2, 100)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().setVisible(False)
        mono = QFont("Consolas, Courier New, monospace")
        mono.setPointSize(10)
        self._table.setFont(mono)
        self._table.setStyleSheet(TABLE_STYLE)
        root.addWidget(self._table, 1)

        # ── Rodapé ───────────────────────────────────────────────────────
        self._lbl_stats = QLabel()
        self._lbl_stats.setStyleSheet("color:#6b7280; font-size:11px;")
        root.addWidget(self._lbl_stats)

    # ------------------------------------------------------------------

    def _load(self):
        idx = self._cmb_limit.currentIndex()
        limit = _LIMITS[idx][1]

        if self._load_worker is not None:
            self._load_worker.loaded.disconnect(self._on_rows_loaded)
            self._load_worker.quit()
            self._load_worker.wait(200)

        self._lbl_stats.setText("Carregando…")
        self._load_worker = _HistoryLoadWorker(
            self._host, limit if limit else 999_999, self
        )
        self._load_worker.loaded.connect(self._on_rows_loaded)
        self._load_worker.start()

    def _on_rows_loaded(self, rows: list):
        self._table.setRowCount(0)
        elapsed_vals = []
        timestamps = []

        for row_data in rows:
            ts_str = datetime.datetime.fromtimestamp(row_data["ts"]).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            ok = row_data["success"]
            ms = row_data["elapsed"]
            note = row_data["note"] or ""

            row = self._table.rowCount()
            self._table.insertRow(row)

            self._set_cell(row, 0, ts_str, "#9ca3af")
            self._set_cell(row, 1, "OK" if ok else "TIMEOUT",
                           "#4ade80" if ok else "#f87171")
            self._set_cell(row, 2, f"{ms:.1f}" if ok else "—",
                           _rtt_color(ms) if ok else "#f87171")
            self._set_cell(row, 3, note, "#6b7280")

            if ok and ms > 0:
                elapsed_vals.append(ms)
                timestamps.append(row_data["ts"])

        # Gráfico
        if elapsed_vals:
            # We must reverse because rows are ordered DESC, but graph needs ascending X
            timestamps.reverse()
            elapsed_vals.reverse()
            
            color = _rtt_color(sum(elapsed_vals) / len(elapsed_vals))
            self._curve.setPen(pg.mkPen(color, width=1.5))
            self._curve.setBrush(pg.mkBrush(color + "18"))
            self._curve.setData(timestamps, elapsed_vals)
            mx = max(elapsed_vals)
            self._plot.setYRange(0, mx * 1.2, padding=0)
        else:
            self._curve.setData([], [])

        # Estatísticas
        total = len(rows)
        ok_n = len(elapsed_vals)
        loss = (total - ok_n) / total * 100 if total else 0
        avg = sum(elapsed_vals) / ok_n if ok_n else 0
        self._lbl_stats.setText(
            f"{total} registros  ·  Perda: {loss:.1f}%  ·  "
            f"Média: {avg:.1f} ms  ·  "
            f"Mín: {min(elapsed_vals):.1f} ms  ·  "
            f"Máx: {max(elapsed_vals):.1f} ms"
            if ok_n else f"{total} registros  ·  sem dados de RTT"
        )

    def _set_cell(self, row: int, col: int, text: str, color: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            if col == 2 else
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        item.setForeground(QColor(color))
        self._table.setItem(row, col, item)

    def _export_csv(self):
        rows = HistoryStore.instance().query(self._host, 999_999)
        if not rows:
            return
        safe = self._host.replace(":", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar histórico", f"history_{safe}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "UNIX ts", "Success", "RTT (ms)", "Nota"])
            for r in rows:
                ts_str = datetime.datetime.fromtimestamp(r["ts"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                writer.writerow([ts_str, r["ts"], r["success"],
                                  f"{r['elapsed']:.3f}", r["note"] or ""])

    def _clear(self):
        reply = QMessageBox.question(
            self, "Limpar histórico",
            f"Apagar todo o histórico de '{self._host}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            HistoryStore.instance().clear(self._host)
            self._load()
