"""
NOCPing — ui/monitor_tab.py
Aba de monitoramento multi-host estilo vmPing.
"""
import csv
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLineEdit,
    QSpinBox, QComboBox, QScrollArea,
    QLabel, QFrame, QLayout, QLayoutItem, QSizePolicy, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize, QPoint, QTimer

from core.models import ProbeConfig, ProbeMode, IPVersion, HostStatus
from core.config_store import save_hosts, load_hosts
from .widgets.host_card import HostCard
from .widgets._utils import field_label as _lbl, parse_host_port
from .theme.tokens import DARK, SPACING, RADIUS
from .theme.components import card_frame, primary_button, secondary_button, danger_button
from .widgets._reflow_row import ReflowRow


class MonitorTab(QWidget):
    status_changed      = pyqtSignal()
    host_status_changed = pyqtSignal(str, object, object)  # host, old, new

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: list[HostCard] = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        root.setSpacing(0)

        # ── Painel de controles (card único: adicionar host + ações globais) ──
        panel = card_frame(RADIUS.md)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        panel_layout.setSpacing(SPACING.sm)

        # Grid: linha 0 = rótulos, linha 1 = campos (mesmas colunas → alinhamento garantido)
        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING.sm)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)   # host — expansível
        # colunas 1-4 têm largura fixa determinada pelos widgets

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("PORTA"),     0, 1)
        grid.addWidget(_lbl("MODO"),      0, 2)
        grid.addWidget(_lbl("VERSÃO IP"), 0, 3)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("ex: 8.8.8.8 ou google.com")
        self._inp_host.setFixedHeight(34)
        self._inp_host.setMinimumWidth(120)
        self._inp_host.returnPressed.connect(self._add_card)

        self._inp_port = QSpinBox()
        self._inp_port.setRange(1, 65535)
        self._inp_port.setValue(443)
        self._inp_port.setFixedHeight(34)
        self._inp_port.setFixedWidth(85)

        self._cmb_mode = QComboBox()
        for m in ProbeMode:
            self._cmb_mode.addItem(m.value, m)
        self._cmb_mode.setFixedHeight(34)
        self._cmb_mode.setFixedWidth(90)
        self._cmb_mode.currentIndexChanged.connect(self._on_mode_changed)
        self._cmb_mode.setCurrentIndex(self._cmb_mode.findData(ProbeMode.ICMP))

        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedHeight(34)
        self._cmb_ip.setFixedWidth(80)

        btn_add = primary_button("Adicionar Host", icon="＋")
        btn_add.setFixedHeight(34)
        btn_add.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_add.clicked.connect(self._add_card)

        grid.addWidget(self._inp_host,  1, 0)
        grid.addWidget(self._inp_port,  1, 1)
        grid.addWidget(self._cmb_mode,  1, 2)
        grid.addWidget(self._cmb_ip,    1, 3)
        grid.addWidget(btn_add,         1, 4)
        panel_layout.addLayout(grid)

        # Divisor
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet("color:palette(mid);")
        panel_layout.addWidget(div)

        # Linha 3 — ações globais. ReflowRow em vez de QHBoxLayout puro:
        # mesmo sintoma do Port Scan em janelas estreitas (perto do mínimo
        # 800x500) — "Limpar Todos" cortava pra "Limpar Todo". Ver
        # docs/redesign/VERIFICACAO_FASE3.md.
        lbl_global = _lbl("CONTROLES GLOBAIS")

        left_widgets = [lbl_global, 4]
        for text, slot, danger in [
            ("Iniciar Todos", self._start_all, False),
            ("Parar Todos",  self._stop_all,  False),
            ("Limpar Todos", self._clear_all, True),
        ]:
            icon = {"Iniciar Todos": "▶", "Parar Todos": "⏹", "Limpar Todos": "🗑"}[text]
            btn = danger_button(text, icon=icon) if danger else secondary_button(text, icon=icon)
            btn.setFixedHeight(28)
            btn.clicked.connect(slot)
            left_widgets.append(btn)

        right_widgets = []
        for text, icon, slot in [("CSV", "💾", self._export_csv), ("JSON", "{ }", self._export_json)]:
            btn_exp = secondary_button(text, icon=icon)
            btn_exp.setFixedHeight(28)
            btn_exp.clicked.connect(slot)
            right_widgets.append(btn_exp)

        action_row = ReflowRow(left=left_widgets, right=right_widgets, spacing=SPACING.sm)
        panel_layout.addWidget(action_row)

        root.addWidget(panel)
        root.addSpacing(SPACING.md)

        # ── Área de cards ───────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background: transparent;")
        self._flow = _FlowLayout(self._cards_container, h_spacing=12, v_spacing=12)
        scroll.setWidget(self._cards_container)
        root.addWidget(scroll, 1)

        # Placeholder vazio
        self._placeholder = QLabel(
            "Nenhum host monitorado.\n\n"
            "Digite um endereço no campo acima e clique em  ＋ Adicionar Host."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet(
            f"color:{DARK.border}; font-size:14px; line-height:1.8;"
        )
        root.addWidget(self._placeholder)

        QTimer.singleShot(0, self._restore_hosts)

    # ------------------------------------------------------------------

    def _restore_hosts(self):
        for cfg in load_hosts():
            self._add_card_from_config(cfg)

    def _add_card_from_config(self, cfg: ProbeConfig):
        card = HostCard(cfg)
        card.removed.connect(self._remove_card)
        card.status_changed.connect(self.host_status_changed)
        self._cards.append(card)
        self._flow.addWidget(card)
        self._placeholder.setVisible(False)

    def _add_card(self):
        host = self._inp_host.text().strip()
        if not host:
            self._inp_host.setFocus()
            return
        host, port = parse_host_port(host)
        if port is not None:
            # "host:porta" (ex: 8.8.8.8:53) — preenche porta+TCP automático
            self._inp_port.setValue(port)
            idx = self._cmb_mode.findData(ProbeMode.TCP)
            if idx >= 0:
                self._cmb_mode.setCurrentIndex(idx)
        cfg = ProbeConfig(
            host=host,
            port=self._inp_port.value(),
            mode=self._cmb_mode.currentData(),
            ip_version=self._cmb_ip.currentData(),
        )
        self._add_card_from_config(cfg)
        save_hosts(self._cards)
        self._inp_host.clear()
        self._inp_host.setFocus()
        self.status_changed.emit()

    def _remove_card(self, card: HostCard):
        card.stop()
        self._cards.remove(card)
        self._flow.removeWidget(card)
        card.deleteLater()
        self._placeholder.setVisible(len(self._cards) == 0)
        save_hosts(self._cards)
        self.status_changed.emit()

    def _start_all(self):
        for c in self._cards:
            c.start()

    def _stop_all(self):
        for c in self._cards:
            c.stop()

    def _clear_all(self):
        from PyQt6.QtWidgets import QMessageBox
        if not self._cards:
            return
        reply = QMessageBox.question(
            self, "Limpar Todos",
            "Tem certeza que deseja remover todos os hosts monitorados?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for c in list(self._cards):
                self._remove_card(c)
            save_hosts([])

    def _on_mode_changed(self):
        is_icmp = self._cmb_mode.currentData() == ProbeMode.ICMP
        self._inp_port.setEnabled(not is_icmp)
        self._inp_port.setToolTip("ICMP não usa porta" if is_icmp else "")

    def _export_csv(self):
        from core.network import calc_stats
        if not self._cards:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Monitor CSV", "nocping_monitor.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Host", "Modo", "Status", "RTT (ms)", "Média (ms)",
                             "Mín (ms)", "Máx (ms)", "Perda %", "Seq"])
            for card in self._cards:
                stats = calc_stats(list(card._results))
                last_rtt = card._results[-1].elapsed_ms if card._results and card._results[-1].success else 0.0
                writer.writerow([
                    card.config.host,
                    card.config.mode.value,
                    card.status.name,
                    f"{last_rtt:.1f}", f"{stats['avg_ms']:.1f}",
                    f"{stats['min_ms']:.1f}", f"{stats['max_ms']:.1f}",
                    f"{stats['loss_pct']:.1f}", len(card._results),
                ])

    def _export_json(self):
        if not self._cards:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar Monitor JSON", "nocping_monitor.json", "JSON (*.json)"
        )
        if not path:
            return
        data = []
        for card in self._cards:
            data.append({
                "host": card.config.host,
                "mode": card.config.mode.value,
                "status": card.status.name,
                "results": [
                    {"seq": r.seq, "success": r.success,
                     "elapsed_ms": r.elapsed_ms, "note": r.note}
                    for r in card._results
                ],
            })
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def card_counts(self) -> tuple:
        total = len(self._cards)
        up   = sum(1 for c in self._cards if c.status == HostStatus.UP)
        down = sum(1 for c in self._cards if c.status == HostStatus.DOWN)
        return total, up, down


# ---------------------------------------------------------------------------
# FlowLayout
# ---------------------------------------------------------------------------

class _FlowLayout(QLayout):
    def __init__(self, parent=None, h_spacing=8, v_spacing=8):
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h = h_spacing
        self._v = v_spacing

    def addItem(self, item):
        self._items.append(item)

    def addWidget(self, widget):
        from PyQt6.QtWidgets import QWidgetItem
        self.addItem(QWidgetItem(widget))
        widget.setParent(self.parentWidget())
        widget.show()
        self.invalidate()

    def removeWidget(self, widget):
        self._items = [i for i in self._items if i.widget() is not widget]
        widget.setParent(None)
        self.invalidate()

    def count(self):                return len(self._items)
    def itemAt(self, i):            return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i):            return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self):  return Qt.Orientation(0)
    def hasHeightForWidth(self):    return True
    def heightForWidth(self, w):    return self._do_layout(QRect(0, 0, w, 0), test=True)
    def setGeometry(self, r):       super().setGeometry(r); self._do_layout(r, test=False)
    def sizeHint(self):             return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect, test):
        m = self.contentsMargins()
        eff = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, row_h = eff.x(), eff.y(), 0
        for item in self._items:
            w = item.widget()
            if w and not w.isVisible():
                continue
            iw, ih = item.sizeHint().width(), item.sizeHint().height()
            nx = x + iw + self._h
            if nx - self._h > eff.right() and row_h > 0:
                x, y, row_h = eff.x(), y + row_h + self._v, 0
                nx = x + iw + self._h
            if not test:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x, row_h = nx, max(row_h, ih)
        return y + row_h - rect.y() + m.bottom()
