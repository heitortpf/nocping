"""
NOCPing — ui/widgets/sidebar.py
Sidebar de navegação vertical — substitui a QTabBar do QTabWidget que ficava
no topo da janela. Cada item é um botão checkable (exclusivo via
QButtonGroup); o ícone é recolorido manualmente no toggle (qtawesome "queima"
a cor no momento da criação — não existe re-tintagem automática por estado
como em QSS, ver docs/DESIGN_SYSTEM.md).

Este widget não sabe nada sobre lazy-loading de aba — só emite
`page_changed(index)` quando o usuário clica um item. MainWindow decide o
que fazer com isso (ver _on_tab_activated em ui/main_window.py).
"""
import qtawesome as qta

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup, QLabel
from PyQt6.QtCore import pyqtSignal, QSize

from ..theme.tokens import DARK, SPACING, RADIUS

_ICON_PX = QSize(16, 16)

# (ícone qtawesome, rótulo) — mesma ordem/seções do QTabWidget original
SECTIONS: list[tuple[str, str]] = [
    ("fa5s.bolt",       "Quick Ping"),
    ("fa5s.circle",     "Monitor"),
    ("fa5s.search",     "Port Scan"),
    ("fa5s.lock",       "Banner / TLS"),
    ("fa5s.route",      "Traceroute"),
    ("fa5s.chart-bar",  "MTR"),
]

_ITEM_QSS = (
    f"QPushButton{{background:transparent;color:{DARK.tab_fg_inactive};text-align:left;"
    f"border:none;border-radius:{RADIUS.sm}px;padding:{SPACING.sm}px {SPACING.md}px;"
    f"font-size:13px;}}"
    f"QPushButton:hover:!checked{{background:palette(mid);color:palette(text);}}"
    f"QPushButton:checked{{background:{DARK.primary};color:{DARK.on_primary};font-weight:bold;}}"
)


class NavSidebar(QWidget):
    page_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavSidebar")
        self.setFixedWidth(180)
        self.setStyleSheet(
            "#NavSidebar{background:palette(alternate-base);border-right:1px solid palette(mid);}"
        )
        self._buttons: list[QPushButton] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING.sm, SPACING.md, SPACING.sm, SPACING.md)
        layout.setSpacing(2)

        brand = QLabel("⬡  NOCPing")
        brand.setStyleSheet(
            f"color:palette(text); font-size:15px; font-weight:700; "
            f"padding:0 {SPACING.md}px {SPACING.md}px {SPACING.md}px;"
        )
        layout.addWidget(brand)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for index, (icon_name, label) in enumerate(SECTIONS):
            btn = QPushButton(f"  {label}")
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setStyleSheet(_ITEM_QSS)
            btn.setIcon(qta.icon(icon_name, color=DARK.tab_fg_inactive))
            btn.setIconSize(_ICON_PX)
            btn.toggled.connect(
                lambda checked, b=btn, name=icon_name: self._recolor_icon(b, name, checked)
            )
            btn.clicked.connect(lambda _checked, i=index: self.page_changed.emit(i))
            self._group.addButton(btn, index)
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

    def _recolor_icon(self, btn: QPushButton, icon_name: str, checked: bool):
        color = DARK.on_primary if checked else DARK.tab_fg_inactive
        btn.setIcon(qta.icon(icon_name, color=color))

    def set_current(self, index: int):
        """Seleciona um item programaticamente, sem emitir page_changed
        (setChecked() não dispara `clicked`, só `toggled` — o ícone é
        recolorido, mas MainWindow não recebe um page_changed redundante)."""
        self._buttons[index].setChecked(True)
