"""
NOCPing — ui/banner_tab.py
Aba de Banner Grab + inspeção TLS/SSL.

Redesenhada para usar o design system (ui/theme/): card de conexão com
respiro (tokens de espaçamento), e as duas naturezas de resultado — banner
HTTP cru e detalhes do certificado TLS — separadas em cards próprios com
section_label(). Ícones de emoji trocados por qtawesome nesta aba (ver
docs/DESIGN_SYSTEM.md, seção "Ícones").
"""
import qtawesome as qta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QPlainTextEdit, QTableWidget,
    QTableWidgetItem, QLabel, QHeaderView, QSplitter,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.models import IPVersion
from core.workers import BannerWorker
from .widgets._utils import field_label as _lbl, TABLE_STYLE
from .widgets._worker_tab import WorkerTabMixin
from .theme.tokens import DARK, SPACING, RADIUS
from .theme.components import card_frame, primary_button, section_label

_ICON_PX = QSize(14, 14)


def _icon_label(icon_name: str, color: str) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(qta.icon(icon_name, color=color).pixmap(_ICON_PX))
    return lbl


def _section_header(icon_name: str, text: str) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACING.xs)
    layout.addWidget(_icon_label(icon_name, DARK.primary))
    layout.addWidget(section_label(text))
    layout.addStretch()
    return row


class BannerTab(WorkerTabMixin, QWidget):
    banner_finished = pyqtSignal(str, int, bool)
    _WORKER_WAIT_MS = 1000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: BannerWorker | None = None
        self._last_success = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        root.setSpacing(SPACING.md)

        # ── Card de conexão ──────────────────────────────────────────
        conn_card = card_frame(RADIUS.md)
        conn_layout = QVBoxLayout(conn_card)
        conn_layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        conn_layout.setSpacing(SPACING.sm)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING.sm)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(0, 1)  # host — expansível

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("PORTA"), 0, 1)
        grid.addWidget(_lbl("TIMEOUT"), 0, 2)
        grid.addWidget(_lbl("VERSÃO IP"), 0, 3)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("Host ou IP")
        self._inp_host.setFixedHeight(34)
        self._inp_host.setMinimumWidth(180)
        self._inp_host.returnPressed.connect(self._connect)

        self._inp_port = QSpinBox()
        self._inp_port.setRange(1, 65535)
        self._inp_port.setValue(443)
        self._inp_port.setFixedHeight(34)
        self._inp_port.setFixedWidth(90)
        self._inp_port.setPrefix(":")

        self._inp_timeout = QSpinBox()
        self._inp_timeout.setRange(500, 30000)
        self._inp_timeout.setValue(2000)
        self._inp_timeout.setSuffix(" ms")
        self._inp_timeout.setFixedHeight(34)
        self._inp_timeout.setFixedWidth(115)

        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedHeight(34)
        self._cmb_ip.setFixedWidth(80)

        self._btn_connect = primary_button("Conectar")
        self._btn_connect.setIcon(qta.icon("fa5s.plug", color=DARK.on_primary))
        self._btn_connect.setFixedHeight(34)
        self._btn_connect.clicked.connect(self._connect)

        grid.addWidget(self._inp_host, 1, 0)
        grid.addWidget(self._inp_port, 1, 1)
        grid.addWidget(self._inp_timeout, 1, 2)
        grid.addWidget(self._cmb_ip, 1, 3)
        grid.addWidget(self._btn_connect, 1, 4)

        conn_layout.addLayout(grid)
        root.addWidget(conn_card)

        # ── Status de conexão ────────────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setSpacing(SPACING.xs)
        self._status_icon = _icon_label("fa5s.circle", DARK.text_muted)
        self._status_icon.setVisible(False)  # só aparece a partir do 1º status
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet("font-size:12px; color:palette(placeholder-text);")
        status_row.addWidget(self._status_icon)
        status_row.addWidget(self._lbl_status, 1)
        root.addLayout(status_row)

        # ── Splitter: card Banner HTTP (cima) + card TLS (baixo) ─────
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setHandleWidth(4)

        # Banner HTTP
        banner_card = card_frame(RADIUS.md)
        bv = QVBoxLayout(banner_card)
        bv.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        bv.setSpacing(SPACING.xs)
        bv.addWidget(_section_header("fa5s.file-alt", "Banner HTTP"))

        self._txt_banner = QPlainTextEdit()
        self._txt_banner.setReadOnly(True)
        self._txt_banner.setPlaceholderText("Aguardando conexão...")
        mono = QFont("Consolas, Courier New, monospace")
        mono.setPointSize(11)
        self._txt_banner.setFont(mono)
        self._txt_banner.setStyleSheet(
            "QPlainTextEdit{background:transparent;color:palette(text);"
            "border:none;padding:4px;}"
        )
        bv.addWidget(self._txt_banner)
        splitter.addWidget(banner_card)

        # Certificado TLS/SSL
        tls_card = card_frame(RADIUS.md)
        tv = QVBoxLayout(tls_card)
        tv.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        tv.setSpacing(SPACING.xs)

        tls_header_row = QHBoxLayout()
        tls_header_row.setSpacing(SPACING.sm)
        tls_header_row.addWidget(_section_header("fa5s.lock", "Certificado TLS/SSL"))
        self._lbl_tls_status = QLabel("—")
        self._lbl_tls_status.setStyleSheet("font-size:11px; color:palette(placeholder-text);")
        tls_header_row.addWidget(self._lbl_tls_status)
        tv.addLayout(tls_header_row)

        self._tls_table = QTableWidget(0, 2)
        self._tls_table.setHorizontalHeaderLabels(["Atributo", "Detalhe"])
        self._tls_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._tls_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tls_table.setStyleSheet(TABLE_STYLE + "QTableWidget { border:none; }")
        tv.addWidget(self._tls_table)
        splitter.addWidget(tls_card)

        splitter.setSizes([200, 150])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------------

    def _worker_signal_pairs(self):
        return [
            ("result",   "_on_result"),
            ("error",    "_on_error"),
            ("finished", "_on_finished"),
        ]

    def _stop_worker(self):
        self._worker.requestInterruption()

    def _connect(self):
        host = self._inp_host.text().strip()
        if not host:
            return
        self._cleanup_worker()

        self._txt_banner.clear()
        self._tls_table.setRowCount(0)
        self._set_status("Conectando...", "fa5s.circle-notch", DARK.info)
        self._lbl_tls_status.setText("—")
        self._btn_connect.setEnabled(False)

        port = self._inp_port.value()
        timeout = self._inp_timeout.value()
        ip_version = self._cmb_ip.currentData()

        self._worker = BannerWorker(host, port, ip_version, timeout)
        self._worker.result.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self):
        self._btn_connect.setEnabled(True)
        host = self._inp_host.text().strip()
        port = self._inp_port.value()
        self.banner_finished.emit(host, port, self._last_success)

    def _on_result(self, data: dict):
        self._last_success = True
        rtt = data.get("rtt_ms", 0.0)
        self._set_status(f"Conectado — RTT: {rtt:.1f}ms", "fa5s.check-circle", DARK.success)

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
            self._lbl_tls_status.setText("Detectado")
            # color=None → mantém a cor padrão da tabela (palette(text),
            # já correta em ambos os temas); só rows com significado
            # semântico (sucesso/marca/alerta) recebem cor fixa.
            rows = [
                ("Versão TLS",     tls_ver or "—",            DARK.success),
                ("Cifra",          data.get("cipher") or "—", None),
                ("Certificado CN", data.get("cn") or "—",     DARK.primary),
                ("Validade",       data.get("expiry") or "—", DARK.warning),
            ]
            self._tls_table.setRowCount(len(rows))
            for i, (attr, val, color) in enumerate(rows):
                self._tls_table.setItem(i, 0, QTableWidgetItem(attr))
                item = QTableWidgetItem(val)
                if color is not None:
                    item.setForeground(QColor(color))
                self._tls_table.setItem(i, 1, item)
        else:
            self._lbl_tls_status.setText("Sem TLS detectado")

    def _on_error(self, msg: str):
        self._last_success = False
        self._set_status(msg, "fa5s.times-circle", DARK.danger)
        self._txt_banner.setPlainText(f"Erro: {msg}")
        self._btn_connect.setEnabled(True)

    # ------------------------------------------------------------------

    def _set_status(self, text: str, icon_name: str, color: str):
        self._status_icon.setPixmap(qta.icon(icon_name, color=color).pixmap(_ICON_PX))
        self._status_icon.setVisible(True)
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet(f"font-size:12px; color:{color};")
