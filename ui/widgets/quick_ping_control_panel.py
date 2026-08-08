"""
NOCPing — ui/widgets/quick_ping_control_panel.py
Painel de controles do Quick Ping — versão compacta: host/protocolo/botões
sempre visíveis; porta/versão IP/contagem/timeout/intervalo viram uma seção
"Avançado" colapsável (fechada por padrão) para não sobrecarregar a aba
inicial da aplicação.

Extraído de ui/quick_ping_tab.py — QuickPingTab é um orquestrador fino que
monta este painel junto com QuickPingGraphPanel/QuickPingConsole/
QuickPingStatsPanel (ver ui/quick_ping_tab.py). A API pública (host_text,
build_config, set_running etc.) não mudou nesta redesign — só a estrutura
interna dos widgets.
"""
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QWidget,
)
from PyQt6.QtCore import pyqtSignal

from core.models import ProbeConfig, ProbeMode, IPVersion
from ._utils import field_label as _lbl, parse_host_port
from ..theme.tokens import SPACING
from ..theme.components import primary_button, secondary_button, toggle_link_button


class QuickPingControlPanel(QFrame):
    ping_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QPPanel")
        self.setStyleSheet("""
            #QPPanel {
                background: palette(alternate-base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        self._build_ui()

    # ------------------------------------------------------------------

    def _build_ui(self):
        panel_layout = QVBoxLayout(self)
        panel_layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        panel_layout.setSpacing(SPACING.sm)

        # ── Linha sempre visível: host + protocolo + ações ────────────
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING.sm)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)  # host — expansível

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("PROTOCOLO"), 0, 1)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("ex: 8.8.8.8, google.com, 2001:4860:4860::8888")
        self._inp_host.setFixedHeight(34)
        self._inp_host.setMinimumWidth(220)
        self._inp_host.returnPressed.connect(self.ping_requested.emit)

        self._cmb_mode = QComboBox()
        for m in ProbeMode:
            self._cmb_mode.addItem(m.value, m)
        self._cmb_mode.setFixedHeight(34)
        self._cmb_mode.setFixedWidth(100)
        # currentIndexChanged só é conectado depois que TODOS os campos (inclusive
        # os da seção Avançado, como _inp_port) existem — _on_mode_changed() lê
        # self._inp_port, e setCurrentIndex() abaixo dispara o sinal na hora.

        self._btn_ping = primary_button("Ping", icon="⚡")
        self._btn_ping.setFixedHeight(34)
        self._btn_ping.setFixedWidth(120)
        self._btn_ping.clicked.connect(self.ping_requested.emit)

        self._btn_stop = secondary_button("Parar", icon="⏹")
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setFixedWidth(100)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self.stop_requested.emit)

        grid.addWidget(self._inp_host, 1, 0)
        grid.addWidget(self._cmb_mode, 1, 1)
        grid.addWidget(self._btn_ping, 1, 2)
        grid.addWidget(self._btn_stop, 1, 3)
        panel_layout.addLayout(grid)

        # ── Seção "Avançado" colapsável ────────────────────────────────
        self._btn_advanced = toggle_link_button(
            "▸  Avançado (porta, versão IP, contagem, timeout, intervalo)"
        )
        self._btn_advanced.toggled.connect(self._toggle_advanced)
        panel_layout.addWidget(self._btn_advanced)

        self._advanced = QWidget()
        adv_grid = QGridLayout(self._advanced)
        adv_grid.setContentsMargins(0, SPACING.xs, 0, 0)
        adv_grid.setHorizontalSpacing(SPACING.sm)
        adv_grid.setVerticalSpacing(2)

        adv_grid.addWidget(_lbl("PORTA"), 0, 0)
        adv_grid.addWidget(_lbl("VERSÃO IP"), 0, 1)
        adv_grid.addWidget(_lbl("CONTAGEM"), 0, 2)
        adv_grid.addWidget(_lbl("TIMEOUT"), 0, 3)
        adv_grid.addWidget(_lbl("INTERVALO"), 0, 4)

        self._inp_port = QSpinBox()
        self._inp_port.setRange(1, 65535)
        self._inp_port.setValue(443)
        self._inp_port.setFixedHeight(34)
        self._inp_port.setFixedWidth(85)

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

        adv_grid.addWidget(self._inp_port, 1, 0)
        adv_grid.addWidget(self._cmb_ip, 1, 1)
        adv_grid.addWidget(self._inp_count, 1, 2)
        adv_grid.addWidget(self._inp_timeout, 1, 3)
        adv_grid.addWidget(self._inp_interval, 1, 4)
        adv_grid.setColumnStretch(5, 1)

        self._advanced.setVisible(False)
        panel_layout.addWidget(self._advanced)

        # Agora que _inp_port (entre outros) já existe, conectar e disparar
        # o estado inicial do modo com segurança.
        self._cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self._cmb_mode.setCurrentIndex(self._cmb_mode.findData(ProbeMode.ICMP))

    def _toggle_advanced(self, checked: bool):
        self._advanced.setVisible(checked)
        self._btn_advanced.setText(
            "▾  Avançado (porta, versão IP, contagem, timeout, intervalo)" if checked
            else "▸  Avançado (porta, versão IP, contagem, timeout, intervalo)"
        )

    def _on_mode_changed(self):
        is_icmp = self._cmb_mode.currentData() == ProbeMode.ICMP
        self._inp_port.setEnabled(not is_icmp)
        self._inp_port.setToolTip("ICMP não usa porta" if is_icmp else "")

    # ------------------------------------------------------------------
    # API pública (usada pelo orquestrador QuickPingTab)
    # ------------------------------------------------------------------

    def host_text(self) -> str:
        raw = self._inp_host.text().strip()
        host, port = parse_host_port(raw)
        if port is not None:
            # "host:porta" (ex: 1.1.1.1:53) — preenche porta+TCP automático
            # e revela a seção Avançado pra dar feedback visual do que mudou.
            self._inp_host.setText(host)
            self._inp_port.setValue(port)
            idx = self._cmb_mode.findData(ProbeMode.TCP)
            if idx >= 0:
                self._cmb_mode.setCurrentIndex(idx)
            if not self._btn_advanced.isChecked():
                self._btn_advanced.setChecked(True)
        return host

    def focus_host(self):
        self._inp_host.setFocus()

    def current_mode(self) -> ProbeMode:
        return self._cmb_mode.currentData()

    def current_port(self) -> int:
        return self._inp_port.value()

    def build_config(self, host: str) -> ProbeConfig:
        return ProbeConfig(
            host=host,
            port=self._inp_port.value(),
            mode=self._cmb_mode.currentData(),
            ip_version=self._cmb_ip.currentData(),
            count=self._inp_count.value(),
            timeout_ms=self._inp_timeout.value(),
            interval_ms=self._inp_interval.value(),
        )

    def set_running(self, running: bool):
        self._btn_ping.setEnabled(not running)
        self._btn_stop.setEnabled(running)
