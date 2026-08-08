"""
NOCPing — ui/widgets/_utils.py
Helpers compartilhados entre abas e widgets.

As constantes/funções aqui agora derivam de ui/theme/tokens.py e
ui/theme/components.py — mantidas com o mesmo nome e valor de sempre para
não exigir mudanças nas abas existentes. Novo código deve importar
diretamente de ui.theme.tokens / ui.theme.components.
"""
import re

from PyQt6.QtWidgets import QLabel

from ..theme.tokens import DARK, TYPOGRAPHY
from ..theme.components import PRIMARY_BTN_QSS

# host + ":" + porta numérica, sem outros ":" no texto — IPv6 puro (múltiplos
# ":", ex. "2001:4860:4860::8888") nunca bate aqui de propósito, então não
# precisa de lógica extra pra distinguir "host:porta" de endereço IPv6.
_HOST_PORT_RE = re.compile(r"^(?P<host>[^:\s]+):(?P<port>\d{1,5})$")


def parse_host_port(text: str) -> tuple[str, int | None]:
    """Separa 'host:porta' (ex: 1.1.1.1:53) em (host, porta).

    Retorna (text, None) quando não há porta explícita reconhecível —
    inclui hosts sem ":", IPv6 sem colchetes e números fora do range
    1-65535 (nesses casos o texto original é devolvido intacto).
    """
    m = _HOST_PORT_RE.match(text)
    if not m:
        return text, None
    port = int(m.group("port"))
    if not (1 <= port <= 65535):
        return text, None
    return m.group("host"), port


def rtt_color(ms: float) -> str:
    """Cor hex baseada na latência: verde/amarelo/vermelho."""
    if ms <= 0:   return DARK.danger
    if ms < 50:   return DARK.success
    if ms < 150:  return DARK.warning
    return DARK.danger


def field_label(text: str) -> QLabel:
    """Rótulo pequeno e muted para campos de formulário."""
    lbl = QLabel(text)
    style = TYPOGRAPHY.label
    lbl.setStyleSheet(
        f"color:{DARK.text_muted}; font-size:{style.size}px; letter-spacing:0.5px;"
    )
    return lbl


PRIMARY_BTN_STYLE = PRIMARY_BTN_QSS

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
