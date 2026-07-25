"""
NOCPing — ui/widgets/quick_ping_console.py
Console de log do Quick Ping — toolbar (recolher/Limpar/Copiar/CSV) + área
de texto estilo terminal, com auto-scroll e cópia. Fundo do terminal usa
`surface_elevated` do design system (mais recuado que o resto dos cards, que
usam `surface`/`palette(base)`) para parecer um terminal de verdade.

Extraído de ui/quick_ping_tab.py. A exportação de CSV depende dos resultados
acumulados pelo orquestrador (QuickPingTab), então o botão "💾 CSV" só emite
`export_requested` — quem sabe o que exportar e abre o diálogo de arquivo é o
orquestrador, não este widget.
"""
from datetime import datetime

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QApplication,
)
from PyQt6.QtCore import pyqtSignal

from core.models import PingResult
from ..theme.tokens import DARK, LIGHT, SPACING, RADIUS


def _console_qss(t) -> str:
    sel_color = f"selection-color: {t.on_primary};" if t is LIGHT else ""
    return f"""
        QPlainTextEdit {{
            background: {t.surface_elevated};
            color: {t.text_primary};
            border: 1px solid {t.border};
            border-radius: {RADIUS.sm}px;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 12px;
            padding: {SPACING.xs}px;
            selection-background-color: {t.primary};
            {sel_color}
        }}
    """


_CONSOLE_STYLE_DARK = _console_qss(DARK)
_CONSOLE_STYLE_LIGHT = _console_qss(LIGHT)

_TOOLBAR_BTN = (
    "QPushButton{background:palette(button);color:palette(button-text);"
    "border-radius:4px;font-size:11px;border:none;padding:2px 10px;}"
    "QPushButton:hover{background:palette(mid);}"
)

_COLLAPSE_BTN = (
    "QPushButton{background:transparent;color:palette(text);"
    "border-radius:4px;font-size:11px;border:none;padding:2px 6px;}"
    "QPushButton:hover{background:palette(mid);}"
)


class QuickPingConsole(QFrame):
    # Cap de blocos do QPlainTextEdit — evita o custo de re-render/scroll
    # crescer sem limite com um teste de ping rodando por horas. Continua
    # exatamente como era antes da redesign (só a cor do terminal mudou).
    MAX_CONSOLE_LINES = 5000
    export_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QPConsoleFrame")
        self.setStyleSheet("""
            #QPConsoleFrame {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        self._layout = layout

        self._toolbar = QHBoxLayout()
        self._toolbar.setSpacing(6)

        self._btn_collapse = QPushButton("▾")
        self._btn_collapse.setCheckable(True)
        self._btn_collapse.setChecked(True)
        self._btn_collapse.setFixedSize(22, 22)
        self._btn_collapse.setStyleSheet(_COLLAPSE_BTN)
        self._btn_collapse.toggled.connect(self._toggle_collapse)
        self._toolbar.addWidget(self._btn_collapse)

        title = QLabel("Console")
        title.setStyleSheet(
            "color:palette(text); font-size:11px; font-weight:bold; letter-spacing:0.5px;"
        )
        self._toolbar.addWidget(title)
        self._toolbar.addStretch()

        for text, slot in [
            ("🗑 Limpar", self.clear),
            ("📋 Copiar", self._copy),
            ("💾 CSV", self.export_requested.emit),
        ]:
            btn = QPushButton(text)
            btn.setFixedHeight(24)
            btn.setStyleSheet(_TOOLBAR_BTN)
            btn.clicked.connect(slot)
            self._toolbar.addWidget(btn)

        layout.addLayout(self._toolbar)

        self._console = QPlainTextEdit()
        self._console.setReadOnly(True)
        self._console.setMaximumBlockCount(self.MAX_CONSOLE_LINES)
        self._console.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._apply_console_theme()
        layout.addWidget(self._console, 1)

    # ------------------------------------------------------------------
    # API pública (usada pelo orquestrador QuickPingTab)
    # ------------------------------------------------------------------

    def log_result(self, r: PingResult, mode: str, port_info: str, ip: str):
        ts = datetime.now().strftime("%H:%M:%S")
        if r.success:
            line = (
                f"[{ts}]  ✅  Reply from {ip}{port_info}: "
                f"time={r.elapsed_ms:.1f}ms seq={r.seq} ({mode})"
            )
        else:
            note = f" — {r.note}" if r.note else ""
            line = f"[{ts}]  ❌  Request timeout seq={r.seq}{note}"
        self._console.appendPlainText(line)

    def log_info(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._console.appendPlainText(f"[{ts}]  ℹ️  {msg}")

    def log_error(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._console.appendPlainText(f"[{ts}]  ⚠️  ERRO: {msg}")

    def clear(self):
        self._console.clear()

    def plain_text(self) -> str:
        return self._console.toPlainText()

    def apply_theme(self, dark: bool):
        self._console.setStyleSheet(
            _CONSOLE_STYLE_DARK if dark else _CONSOLE_STYLE_LIGHT
        )

    # ------------------------------------------------------------------

    def _copy(self):
        text = self._console.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _toggle_collapse(self, expanded: bool):
        self._console.setVisible(expanded)
        self._btn_collapse.setText("▾" if expanded else "▸")
        if expanded:
            self.setMaximumHeight(16777215)  # QWIDGETSIZE_MAX — remove o teto
        else:
            m = self._layout.contentsMargins()
            collapsed_h = self._toolbar.sizeHint().height() + m.top() + m.bottom()
            self.setMaximumHeight(collapsed_h)

    def _apply_console_theme(self):
        app = QApplication.instance()
        dark = True
        if app:
            win_color = app.palette().color(app.palette().ColorRole.Window)
            dark = win_color.lightness() < 128
        self._console.setStyleSheet(
            _CONSOLE_STYLE_DARK if dark else _CONSOLE_STYLE_LIGHT
        )
