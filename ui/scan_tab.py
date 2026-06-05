"""
NOCPing — ui/scan_tab.py
Aba de port scan multithread.
"""
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QProgressBar, QLabel, QHeaderView, QFileDialog, QCheckBox,
)
from PyQt6.QtGui import QColor

from core.models import IPVersion
from core.workers import ScanWorker
from .widgets._utils import PRIMARY_BTN_STYLE, TABLE_STYLE


_PRESETS: list[tuple[str, str]] = [
    ("Personalizado",   ""),
    ("Top 20 – rápido", "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1723,3306,3389,5900,8080,8443"),
    ("Top 100 – comum", "7,9,13,21,22,23,25,26,37,53,79,80,81,88,106,110,111,113,119,135,139,143,"
                        "144,179,199,389,427,443,444,445,465,513,514,515,543,544,548,554,587,631,"
                        "646,873,990,993,995,1025,1026,1027,1028,1029,1110,1433,1720,1723,1755,"
                        "1900,2000,2001,2049,2121,2717,3000,3128,3306,3389,3986,4899,5000,5009,"
                        "5051,5060,5101,5190,5357,5432,5631,5666,5800,5900,6000,6001,6646,7070,"
                        "8000,8008,8009,8080,8081,8443,8888,9100,9999,10000,32768,49152,49153,"
                        "49154,49155,49156,49157"),
    ("Todas (1-65535)", "1-65535"),
]


class ScanTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ScanWorker | None = None
        self._results: list[tuple] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Linha 1: host + predefinição + portas ---
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("Host ou IP")
        self._inp_host.setMinimumWidth(140)

        lbl_pre = QLabel("Predefinição:")
        lbl_pre.setStyleSheet("color:#9ca3af;")
        self._cmb_preset = QComboBox()
        for name, _ in _PRESETS:
            self._cmb_preset.addItem(name)
        self._cmb_preset.setFixedWidth(155)
        self._cmb_preset.currentIndexChanged.connect(self._on_preset_changed)

        self._inp_ports = QLineEdit()
        self._inp_ports.setPlaceholderText("1-1024,3389,8080")
        self._inp_ports.setMinimumWidth(120)
        self._inp_ports.textEdited.connect(self._on_ports_edited)

        row1.addWidget(self._inp_host, 2)
        row1.addWidget(lbl_pre)
        row1.addWidget(self._cmb_preset)
        row1.addWidget(self._inp_ports, 1)
        root.addLayout(row1)

        # --- Linha 2: opções + botões ---
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        lbl_t = QLabel("Timeout:")
        lbl_t.setStyleSheet("color:#9ca3af;")
        self._inp_timeout = QSpinBox()
        self._inp_timeout.setRange(50, 10000)
        self._inp_timeout.setValue(200)
        self._inp_timeout.setSuffix(" ms")
        self._inp_timeout.setFixedWidth(110)

        lbl_th = QLabel("Threads:")
        lbl_th.setStyleSheet("color:#9ca3af;")
        self._inp_threads = QSpinBox()
        self._inp_threads.setRange(1, 512)
        self._inp_threads.setValue(200)
        self._inp_threads.setFixedWidth(80)

        lbl_ip = QLabel("Versão IP:")
        lbl_ip.setStyleSheet("color:#9ca3af;")
        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedWidth(65)

        lbl_proto = QLabel("Protocolo:")
        lbl_proto.setStyleSheet("color:#9ca3af;")
        self._cmb_proto = QComboBox()
        for label in ("TCP", "UDP", "TCP+UDP"):
            self._cmb_proto.addItem(label, label)
        self._cmb_proto.setFixedWidth(85)

        self._btn_start = QPushButton("▶ Iniciar Scan")
        self._btn_start.setFixedHeight(30)
        self._btn_start.setStyleSheet(PRIMARY_BTN_STYLE)
        self._btn_start.clicked.connect(self._start)

        self._btn_stop = QPushButton("⏹ Parar")
        self._btn_stop.setFixedHeight(30)
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            "QPushButton{background:palette(button);color:palette(button-text);"
            "border-radius:4px;font-size:12px;border:none;padding:0 8px;}"
            "QPushButton:hover{background:palette(mid);}"
            "QPushButton:disabled{color:palette(placeholder-text);}"
        )
        self._btn_stop.clicked.connect(self._stop)

        self._btn_export = QPushButton("💾 Exportar CSV")
        self._btn_export.setFixedHeight(30)
        self._btn_export.setEnabled(False)
        self._btn_export.setStyleSheet(
            "QPushButton{background:palette(button);color:palette(button-text);"
            "border-radius:4px;font-size:12px;border:none;padding:0 8px;}"
            "QPushButton:hover{background:palette(mid);}"
            "QPushButton:disabled{color:palette(placeholder-text);}"
        )
        self._btn_export.clicked.connect(self._export_csv)

        row2.addWidget(lbl_t)
        row2.addWidget(self._inp_timeout)
        row2.addWidget(lbl_th)
        row2.addWidget(self._inp_threads)
        row2.addWidget(lbl_ip)
        row2.addWidget(self._cmb_ip)
        row2.addWidget(lbl_proto)
        row2.addWidget(self._cmb_proto)

        self._chk_udp_filtered = QCheckBox("UDP open|filtered")
        self._chk_udp_filtered.setStyleSheet("color:#9ca3af; font-size:12px;")
        row2.addWidget(self._chk_udp_filtered)
        row2.addStretch()
        row2.addWidget(self._btn_start)
        row2.addWidget(self._btn_stop)
        row2.addWidget(self._btn_export)
        root.addLayout(row2)

        # --- Barra de progresso + stats ---
        prog_row = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%v / %m portas")
        self._progress.setStyleSheet("""
            QProgressBar {
                background:palette(button); border-radius:4px; color:palette(button-text);
                text-align:center; font-size:11px; height:18px;
            }
            QProgressBar::chunk { background:#7c3aed; border-radius:4px; }
        """)
        self._lbl_open = QLabel("Abertas: 0")
        self._lbl_open.setStyleSheet("color:#4ade80; font-size:12px; min-width:80px;")
        prog_row.addWidget(self._progress, 1)
        prog_row.addWidget(self._lbl_open)
        root.addLayout(prog_row)

        # --- Tabela ---
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Porta", "Proto", "Serviço", "RTT", "Status"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 60)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            TABLE_STYLE + "QTableWidget { alternate-background-color:palette(alternate-base); border:none; }"
        )
        root.addWidget(self._table)

    # ------------------------------------------------------------------

    def _on_preset_changed(self, idx: int):
        _, ports = _PRESETS[idx]
        if ports:
            self._inp_ports.setText(ports)

    def _on_ports_edited(self):
        self._cmb_preset.blockSignals(True)
        self._cmb_preset.setCurrentIndex(0)  # volta para "Personalizado"
        self._cmb_preset.blockSignals(False)

    def _cleanup_worker(self):
        if self._worker is None:
            return
        try:
            self._worker.port_result.disconnect(self._on_port_result)
            self._worker.progress.disconnect(self._on_progress)
            self._worker.finished_ok.disconnect(self._on_finished)
            self._worker.error.disconnect(self._on_error)
        except RuntimeError:
            pass
        if self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        self._worker.deleteLater()
        self._worker = None

    def _start(self):
        host = self._inp_host.text().strip()
        if not host:
            return

        self._cleanup_worker()

        self._results.clear()
        self._table.setRowCount(0)
        self._open_count = 0
        self._lbl_open.setText("Abertas: 0")
        self._btn_export.setEnabled(False)

        port_spec = self._inp_ports.text().strip()
        ip_version = self._cmb_ip.currentData()
        timeout_ms = self._inp_timeout.value()
        threads = self._inp_threads.value()
        protocol = self._cmb_proto.currentData()

        self._worker = ScanWorker(host, port_spec, ip_version, timeout_ms, threads, protocol)
        self._worker.port_result.connect(self._on_port_result)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        from core.network import _parse_ports
        try:
            n_ports = len(_parse_ports(port_spec))
            multiplier = 2 if protocol == "TCP+UDP" else 1
            total = n_ports * multiplier
        except Exception:
            total = 1024
        self._progress.setRange(0, total)
        self._progress.setValue(0)
        self._progress.setFormat(f"%v / {total} portas")

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._worker.start()

    def _stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_port_result(self, port: int, is_open: bool, ms: float, protocol: str):
        is_filtered = (
            not is_open
            and protocol == "UDP"
            and self._chk_udp_filtered.isChecked()
        )
        if not is_open and not is_filtered:
            return

        self._open_count = getattr(self, "_open_count", 0) + 1
        self._lbl_open.setText(f"Abertas: {self._open_count}")
        self._results.append((port, is_open, ms, protocol))

        try:
            import socket
            svc = socket.getservbyport(port, protocol.lower() if protocol in ("TCP", "UDP") else "tcp")
        except OSError:
            svc = "—"

        status_text  = "● Aberta"       if is_open else "◎ open|filtered"
        status_color = "#4ade80"        if is_open else "#facc15"
        proto_color  = "#60a5fa" if protocol == "UDP" else "#a78bfa"
        row = self._table.rowCount()
        self._table.insertRow(row)

        items = [
            (str(port),      "#4ade80"),
            (protocol,       proto_color),
            (svc,            "#9ca3af"),
            (f"{ms:.1f} ms", "#cdd6f4"),
            (status_text,    status_color),
        ]
        for col, (text, color) in enumerate(items):
            item = QTableWidgetItem(text)
            item.setForeground(QColor(color))
            self._table.setItem(row, col, item)

        self._table.scrollToBottom()

    def _on_progress(self, done: int, total: int):
        self._progress.setValue(done)

    def _on_finished(self):
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_export.setEnabled(bool(self._results))

    def _on_error(self, msg: str):
        self._on_finished()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "nocping_scan.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Porta", "Protocolo", "Serviço", "RTT (ms)", "Status"])
            for port, is_open, ms, protocol in self._results:
                try:
                    import socket
                    svc = socket.getservbyport(port, protocol.lower() if protocol in ("TCP", "UDP") else "tcp")
                except OSError:
                    svc = ""
                writer.writerow([port, protocol, svc, f"{ms:.1f}", "Aberta" if is_open else "Fechada"])
