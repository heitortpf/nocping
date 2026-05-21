"""
NOCPing — ui/banner_tab.py
Aba de Banner Grab + inspeção TLS/SSL.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QLabel, QHeaderView, QFrame, QSplitter,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from core.models import IPVersion
from core.workers import BannerWorker
from .widgets._utils import PRIMARY_BTN_STYLE


class BannerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: BannerWorker | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Formulário ---
        form = QHBoxLayout()
        form.setSpacing(6)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("Host ou IP")
        self._inp_host.setMinimumWidth(180)
        self._inp_host.returnPressed.connect(self._connect)

        self._inp_port = QSpinBox()
        self._inp_port.setRange(1, 65535)
        self._inp_port.setValue(443)
        self._inp_port.setFixedWidth(90)
        self._inp_port.setPrefix(":")

        lbl_t = QLabel("Timeout:")
        lbl_t.setStyleSheet("color:#9ca3af;")
        self._inp_timeout = QSpinBox()
        self._inp_timeout.setRange(500, 30000)
        self._inp_timeout.setValue(2000)
        self._inp_timeout.setSuffix(" ms")
        self._inp_timeout.setFixedWidth(115)

        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedWidth(65)

        self._btn_connect = QPushButton("▶ Conectar")
        self._btn_connect.setFixedHeight(30)
        self._btn_connect.setStyleSheet(PRIMARY_BTN_STYLE)
        self._btn_connect.clicked.connect(self._connect)

        for w in (self._inp_host, self._inp_port,
                  lbl_t, self._inp_timeout,
                  self._cmb_ip, self._btn_connect):
            form.addWidget(w)
        form.addStretch()
        root.addLayout(form)

        # --- Status de conexão ---
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet("font-size:12px; color:#9ca3af;")
        root.addWidget(self._lbl_status)

        # --- Splitter: Banner (cima) + TLS (baixo) ---
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        # Banner
        banner_frame = QFrame()
        bv = QVBoxLayout(banner_frame)
        bv.setContentsMargins(0, 0, 0, 0)
        bv.setSpacing(4)
        lbl_banner = QLabel("Banner recebido:")
        lbl_banner.setStyleSheet("color:#9ca3af; font-size:11px;")
        self._txt_banner = QPlainTextEdit()
        self._txt_banner.setReadOnly(True)
        self._txt_banner.setPlaceholderText(
            "Aguardando conexão..."
        )
        mono = QFont("Consolas, Courier New, monospace")
        mono.setPointSize(11)
        self._txt_banner.setFont(mono)
        self._txt_banner.setStyleSheet(
            "QPlainTextEdit{background:palette(base);color:palette(text);"
            "border:1px solid palette(mid);border-radius:4px;padding:6px;}"
        )
        bv.addWidget(lbl_banner)
        bv.addWidget(self._txt_banner)
        splitter.addWidget(banner_frame)

        # TLS
        tls_frame = QFrame()
        tv = QVBoxLayout(tls_frame)
        tv.setContentsMargins(0, 0, 0, 0)
        tv.setSpacing(4)
        self._lbl_tls_title = QLabel("TLS / Criptografia:")
        self._lbl_tls_title.setStyleSheet("color:#9ca3af; font-size:11px;")
        self._tls_table = QTableWidget(0, 2)
        self._tls_table.setHorizontalHeaderLabels(["Atributo", "Detalhe"])
        self._tls_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._tls_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tls_table.setStyleSheet("""
            QTableWidget {
                background:palette(base); color:palette(text);
                border:1px solid palette(mid); border-radius:4px;
                font-size:12px; gridline-color:palette(mid);
            }
            QHeaderView::section {
                background:palette(button); color:palette(button-text);
                border:none; padding:4px;
            }
        """)
        tv.addWidget(self._lbl_tls_title)
        tv.addWidget(self._tls_table)
        splitter.addWidget(tls_frame)

        splitter.setSizes([200, 150])
        root.addWidget(splitter)

    # ------------------------------------------------------------------

    def _cleanup_worker(self):
        if self._worker is None:
            return
        try:
            self._worker.result.disconnect(self._on_result)
            self._worker.error.disconnect(self._on_error)
            self._worker.finished.disconnect()
        except RuntimeError:
            pass
        if self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(1000)
        self._worker.deleteLater()
        self._worker = None

    def _connect(self):
        host = self._inp_host.text().strip()
        if not host:
            return
        self._cleanup_worker()

        self._txt_banner.clear()
        self._tls_table.setRowCount(0)
        self._lbl_status.setText("Conectando...")
        self._lbl_tls_title.setText("TLS / Criptografia:")
        self._btn_connect.setEnabled(False)

        port = self._inp_port.value()
        timeout = self._inp_timeout.value()
        ip_version = self._cmb_ip.currentData()

        self._worker = BannerWorker(host, port, ip_version, timeout)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(lambda: self._btn_connect.setEnabled(True))
        self._worker.start()

    def _on_result(self, data: dict):
        rtt = data.get("rtt_ms", 0.0)
        self._lbl_status.setText(
            f"<span style='color:#4ade80;'>● Conectado</span>"
            f"  RTT: <span style='color:#7c3aed;'>{rtt:.1f}ms</span>"
        )
        self._lbl_status.setTextFormat(Qt.TextFormat.RichText)

        banner = data.get("banner", "")
        if banner:
            self._txt_banner.setPlainText(banner)
        else:
            self._txt_banner.setPlainText(
                "(Nenhum banner textual recebido — "
                "o serviço pode exigir criptografia ou protocolo específico.)"
            )

        # TLS
        tls_ver = data.get("tls_version")
        if tls_ver:
            self._lbl_tls_title.setText("🔒 TLS Detectado:")
            rows = [
                ("Versão TLS",   tls_ver or "—",               "#4ade80"),
                ("Cifra",        data.get("cipher") or "—",    "#cdd6f4"),
                ("Certificado CN", data.get("cn") or "—",      "#7c3aed"),
                ("Validade",     data.get("expiry") or "—",    "#facc15"),
            ]
            self._tls_table.setRowCount(len(rows))
            for i, (attr, val, color) in enumerate(rows):
                self._tls_table.setItem(i, 0, QTableWidgetItem(attr))
                item = QTableWidgetItem(val)
                item.setForeground(QColor(color))
                self._tls_table.setItem(i, 1, item)
        else:
            self._lbl_tls_title.setText("🔓 Sem TLS detectado")

    def _on_error(self, msg: str):
        self._lbl_status.setText(
            f"<span style='color:#f87171;'>✕ {msg}</span>"
        )
        self._lbl_status.setTextFormat(Qt.TextFormat.RichText)
        self._txt_banner.setPlainText(f"Erro: {msg}")
        self._btn_connect.setEnabled(True)
