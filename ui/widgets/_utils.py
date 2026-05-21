"""
NOCPing — ui/widgets/_utils.py
Helpers compartilhados entre abas e widgets.
"""
from PyQt6.QtWidgets import QLabel


def rtt_color(ms: float) -> str:
    """Cor hex baseada na latência: verde/amarelo/vermelho."""
    if ms <= 0:   return "#f87171"
    if ms < 50:   return "#4ade80"
    if ms < 150:  return "#facc15"
    return "#f87171"


def field_label(text: str) -> QLabel:
    """Rótulo pequeno e muted para campos de formulário."""
    lbl = QLabel(text)
    lbl.setStyleSheet("color:#6b7280; font-size:10px; letter-spacing:0.5px;")
    return lbl


PRIMARY_BTN_STYLE = (
    "QPushButton{background:#7c3aed;color:#fff;border-radius:6px;"
    "font-size:13px;font-weight:bold;border:none;padding:0 16px;}"
    "QPushButton:hover{background:#6d28d9;}"
    "QPushButton:pressed{background:#5b21b6;}"
)

TABLE_STYLE = """
    QTableWidget {
        background:palette(base); color:palette(text);
        border:1px solid palette(mid); border-radius:4px;
        font-size:12px; gridline-color:palette(mid);
    }
    QHeaderView::section {
        background:palette(button); color:palette(button-text);
        border:none; padding:4px; font-size:11px;
    }
"""
