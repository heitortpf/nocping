"""
NOCPing — ui/mtr_tab.py
Aba MTR (My TraceRoute): traceroute contínuo com estatísticas por hop.

Redesenhada para usar o design system (ui/theme/): card de controle mais
compacto (Host/Versão IP sempre visíveis; Max Hops/Timeout/Intervalo viram
uma seção "Avançado" colapsável, escondida por padrão), aviso de privilégio
insuficiente reaproveitado de traceroute_tab.py, e cores da tabela por token.
MTRWorker e a lógica de hop_discovered/hop_update não foram alterados — só
a camada visual.
"""
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QTableWidget, QTableWidgetItem,
    QLabel, QHeaderView, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPalette

from core.models import IPVersion
from core.network import is_admin
from core.workers import MTRWorker
from .widgets._utils import field_label as _lbl, rtt_color as _rtt_color, TABLE_STYLE
from .widgets._worker_tab import WorkerTabMixin
from .theme.tokens import DARK, SPACING, RADIUS
from .theme.components import (
    card_frame, primary_button, secondary_button, admin_warning, toggle_link_button,
)

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
    # Consolidado para os 3 tokens de status do design system (antes eram 4
    # tons distintos: verde/lima/amarelo/vermelho — lima e verde viraram o
    # mesmo `success`, ver relatório da tarefa).
    if pct < 5:
        return DARK.success
    if pct < 20:
        return DARK.warning
    return DARK.danger


class MTRTab(WorkerTabMixin, QWidget):
    mtr_finished = pyqtSignal(str, int)
    _WORKER_WAIT_GUARDED = False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: MTRWorker | None = None
        self._row_map: dict[int, int] = {}  # ttl -> row index
        self._manually_stopped = False
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        root.setSpacing(SPACING.md)

        # ── Card de controle (compacto: Host + Versão IP sempre visíveis) ──
        panel = card_frame(RADIUS.md)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        pl.setSpacing(SPACING.sm)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING.sm)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("VERSÃO IP"), 0, 1)

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

        self._btn_start = primary_button("Iniciar MTR", icon="▶")
        self._btn_start.setFixedHeight(34)
        self._btn_start.clicked.connect(self._start)

        self._btn_stop = secondary_button("Parar", icon="⏹")
        self._btn_stop.setFixedHeight(34)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)

        grid.addWidget(self._inp_host, 1, 0)
        grid.addWidget(self._cmb_ip,   1, 1)
        grid.addWidget(self._btn_start, 1, 2)
        grid.addWidget(self._btn_stop,  1, 3)
        pl.addLayout(grid)

        if not is_admin():
            pl.addWidget(admin_warning(
                "Sem privilégios de Administrador — MTR (raw socket ICMP) não vai funcionar."
            ))

        # ── Seção "Avançado" colapsável: Max Hops / Timeout / Intervalo ──
        self._btn_advanced = toggle_link_button("▸  Avançado (max hops, timeout, intervalo)")
        self._btn_advanced.toggled.connect(self._toggle_advanced)
        pl.addWidget(self._btn_advanced)

        self._advanced = QWidget()
        adv_grid = QGridLayout(self._advanced)
        adv_grid.setContentsMargins(0, SPACING.xs, 0, 0)
        adv_grid.setHorizontalSpacing(SPACING.sm)
        adv_grid.setVerticalSpacing(2)

        adv_grid.addWidget(_lbl("MAX HOPS"),  0, 0)
        adv_grid.addWidget(_lbl("TIMEOUT"),   0, 1)
        adv_grid.addWidget(_lbl("INTERVALO"), 0, 2)

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

        adv_grid.addWidget(self._spn_hops,     1, 0)
        adv_grid.addWidget(self._spn_timeout,  1, 1)
        adv_grid.addWidget(self._spn_interval, 1, 2)
        adv_grid.setColumnStretch(3, 1)

        self._advanced.setVisible(False)
        pl.addWidget(self._advanced)

        root.addWidget(panel)

        # ── Status + ações ──────────────────────────────────────────────
        self._lbl_status = QLabel("Digite um host e clique em Iniciar MTR.")
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

        # ── Tabela ──────────────────────────────────────────────────────
        headers = ["Hop", "IP", "Hostname", "Loss%", "Sent",
                   "Last", "Avg", "Best", "Worst", "StDev"]
        self._table = QTableWidget(0, len(headers))
        self._table.setHorizontalHeaderLabels(headers)
        hdr = self._table.horizontalHeader()
        # Interactive (não Fixed) em todas as colunas exceto Hostname: dá pra
        # arrastar a borda pra redimensionar, igual planilha — e Qt já trata
        # duplo-clique na borda como "auto-ajustar ao conteúdo" de graça no
        # modo Interactive, sem código extra. Hostname continua Stretch pra
        # ocupar o espaço sobrando. Largura inicial da coluna IP subiu (150 →
        # 190) porque IPv6 sem abreviar (ex: 2804:3230:88:5700:2eb:d8ff:...)
        # cortava com "..." no tamanho antigo; ainda assim cabe redimensionar
        # mais, e o tooltip por célula (ver _set_cell) mostra o valor
        # completo mesmo sem redimensionar.
        for col, mode in [
            (_COL_HOP,      QHeaderView.ResizeMode.Interactive),
            (_COL_IP,       QHeaderView.ResizeMode.Interactive),
            (_COL_HOSTNAME, QHeaderView.ResizeMode.Stretch),
            (_COL_LOSS,     QHeaderView.ResizeMode.Interactive),
            (_COL_SENT,     QHeaderView.ResizeMode.Interactive),
            (_COL_LAST,     QHeaderView.ResizeMode.Interactive),
            (_COL_AVG,      QHeaderView.ResizeMode.Interactive),
            (_COL_BEST,     QHeaderView.ResizeMode.Interactive),
            (_COL_WORST,    QHeaderView.ResizeMode.Interactive),
            (_COL_STDEV,    QHeaderView.ResizeMode.Interactive),
        ]:
            hdr.setSectionResizeMode(col, mode)
        self._table.setColumnWidth(_COL_HOP,   46)
        self._table.setColumnWidth(_COL_IP,    190)
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
        self._table.setAlternatingRowColors(True)
        # Fonte monoespaçada em toda a tabela — colunas numéricas (Loss%...
        # StDev) já ficam alinhadas à direita em _set_cell(), então os
        # dígitos formam colunas retas (tipografia tabular "de fato" via
        # fonte monoespaçada, já que Consolas não tem variante "tabular
        # figures" separada — mono já garante isso).
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

    def _toggle_advanced(self, checked: bool):
        self._advanced.setVisible(checked)
        self._btn_advanced.setText(
            "▾  Avançado (max hops, timeout, intervalo)" if checked
            else "▸  Avançado (max hops, timeout, intervalo)"
        )

    def _worker_signal_pairs(self):
        return [
            ("hop_discovered", "_on_hop_discovered"),
            ("hop_update",     "_on_hop_update"),
            ("error",          "_on_error"),
            ("finished",       "_on_finished"),
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
        self._lbl_status.setText(f"Rastreando MTR para  {host}…")
        self._lbl_status.setStyleSheet(f"color:{DARK.info}; font-size:12px; padding:2px 0;")
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
        self._lbl_status.setStyleSheet(f"color:{DARK.text_muted}; font-size:12px; padding:2px 0;")

    def _on_hop_discovered(self, ttl: int, ip: str, hostname: str):
        if ttl in self._row_map:
            row = self._row_map[ttl]
            self._set_cell(row, _COL_IP,       ip or "* * *", DARK.text_muted if not ip else None)
            self._set_cell(row, _COL_HOSTNAME, hostname or "—", DARK.text_muted)
            return
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._row_map[ttl] = row
        self._set_cell(row, _COL_HOP,      str(ttl),       DARK.text_muted)
        self._set_cell(row, _COL_IP,       ip or "* * *",  DARK.text_muted if not ip else None)
        self._set_cell(row, _COL_HOSTNAME, hostname or "—", DARK.text_muted)
        for col in (_COL_LOSS, _COL_SENT, _COL_LAST, _COL_AVG,
                    _COL_BEST, _COL_WORST, _COL_STDEV):
            self._set_cell(row, col, "—", DARK.text_muted)

    def _on_hop_update(self, ttl: int, stats: dict):
        row = self._row_map.get(ttl)
        if row is None:
            return
        loss = stats["loss_pct"]
        self._set_cell(row, _COL_LOSS,  f"{loss:.1f}%",              _loss_color(loss))
        self._set_cell(row, _COL_SENT,  str(stats["sent"]),           DARK.text_muted)
        self._set_cell(row, _COL_LAST,  self._fmt(stats["last_ms"]),  _rtt_color(stats["last_ms"]))
        self._set_cell(row, _COL_AVG,   self._fmt(stats["avg_ms"]),   _rtt_color(stats["avg_ms"]))
        self._set_cell(row, _COL_BEST,  self._fmt(stats["best_ms"]),  DARK.success)
        self._set_cell(row, _COL_WORST, self._fmt(stats["worst_ms"]), _rtt_color(stats["worst_ms"]))
        self._set_cell(row, _COL_STDEV, self._fmt(stats["stdev_ms"]), DARK.text_muted)

        hops = self._table.rowCount()
        sent = stats["sent"]
        self._lbl_status.setText(
            f"MTR ativo — {hops} hop(s) descobertos — {sent} sondas enviadas."
        )

    def _on_error(self, msg: str):
        self._lbl_status.setText(f"Erro: {msg}")
        self._lbl_status.setStyleSheet(f"color:{DARK.danger}; font-size:12px; padding:2px 0;")
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_clear.setEnabled(True)
        self._btn_export.setEnabled(self._table.rowCount() > 0)

    def _on_finished(self):
        self._lbl_status.setText("MTR concluído.")
        self._lbl_status.setStyleSheet(f"color:{DARK.success}; font-size:12px; padding:2px 0;")
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
        self._lbl_status.setStyleSheet(f"color:{DARK.text_muted}; font-size:12px; padding:2px 0;")

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

    def _set_cell(self, row: int, col: int, text: str, color: str | None):
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
        # Tooltip com o texto completo -- IP/hostname (IPv6 sobretudo) corta
        # com "..." mesmo depois de aumentar a largura padrão da coluna;
        # passar o mouse mostra o valor inteiro sem precisar redimensionar.
        item.setToolTip(text)
        # color=None = cor padrão da tabela (palette(text)). Resolvida aqui
        # (não só "pular o setForeground") porque esta célula pode ser
        # reescrita depois com uma cor diferente (ex.: IP muda de "sem
        # resposta ainda" cinza para um IP real com cor padrão) — só pular
        # deixaria a cor antiga grudada no item.
        color_obj = (
            QColor(color) if color is not None
            else self._table.palette().color(QPalette.ColorRole.Text)
        )
        item.setForeground(color_obj)
