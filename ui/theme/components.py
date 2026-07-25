"""
NOCPing — ui/theme/components.py
Builders de widgets estilizados a partir de ui/theme/tokens.py — fonte única
para botões, cards, rótulos de seção e badges de status.

Estas funções são a evolução de PRIMARY_BTN_STYLE/TABLE_STYLE (ainda em
ui/widgets/_utils.py, agora reexportados a partir daqui para não quebrar as
abas existentes). Novas telas e refatorações de abas devem preferir estes
builders em vez de montar QSS inline.
"""
import qtawesome as qta

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.models import HostStatus
from .tokens import DARK, RADIUS, SPACING, TYPOGRAPHY

_WARNING_ICON_PX = QSize(14, 14)


STATUS_COLOR = {
    HostStatus.IDLE:    DARK.text_muted,
    HostStatus.RUNNING: DARK.info,
    HostStatus.UP:      DARK.success,
    HostStatus.DOWN:    DARK.danger,
    HostStatus.ERROR:   DARK.warning,
}

STATUS_LABEL = {
    HostStatus.IDLE:    "INATIVO",
    HostStatus.RUNNING: "INICIANDO…",
    HostStatus.UP:      "ONLINE",
    HostStatus.DOWN:    "OFFLINE",
    HostStatus.ERROR:   "ERRO",
}


def _btn_text(text: str, icon: str | None) -> str:
    return f"{icon}  {text}" if icon else text


# QSS como strings puras em nível de módulo — nada aqui instancia QWidget,
# então importar este módulo não exige uma QApplication já criada.
_DISABLED_BTN_QSS = "QPushButton:disabled{background:palette(button);color:palette(placeholder-text);}"

PRIMARY_BTN_QSS = (
    f"QPushButton{{background:{DARK.primary};color:{DARK.on_primary};"
    f"border-radius:{RADIUS.sm}px;font-size:13px;font-weight:bold;"
    f"border:none;padding:0 {SPACING.lg}px;}}"
    f"QPushButton:hover{{background:{DARK.primary_hover};}}"
    f"QPushButton:pressed{{background:{DARK.primary_press};}}"
    f"{_DISABLED_BTN_QSS}"
)

SECONDARY_BTN_QSS = (
    f"QPushButton{{background:palette(button);color:palette(button-text);"
    f"border-radius:{RADIUS.sm}px;font-size:12px;border:none;"
    f"padding:0 {SPACING.md}px;}}"
    f"QPushButton:hover{{background:palette(mid);}}"
    f"{_DISABLED_BTN_QSS}"
)

DANGER_BTN_QSS = (
    f"QPushButton{{background:{DARK.danger_strong};color:{DARK.on_primary};"
    f"border-radius:{RADIUS.sm}px;font-size:12px;border:none;"
    f"padding:0 {SPACING.md}px;}}"
    f"QPushButton:hover{{background:{DARK.danger_strong_hover};}}"
    f"{_DISABLED_BTN_QSS}"
)


def primary_button(text: str, icon: str | None = None) -> QPushButton:
    """Ação principal da tela (ex.: Adicionar Host, Conectar, Iniciar)."""
    btn = QPushButton(_btn_text(text, icon))
    btn.setStyleSheet(PRIMARY_BTN_QSS)
    return btn


def secondary_button(text: str, icon: str | None = None) -> QPushButton:
    """Ação secundária/neutra (ex.: Parar, Exportar) — segue o tema via palette()."""
    btn = QPushButton(_btn_text(text, icon))
    btn.setStyleSheet(SECONDARY_BTN_QSS)
    return btn


def danger_button(text: str, icon: str | None = None) -> QPushButton:
    """Ação destrutiva (ex.: Limpar Todos, Remover Host)."""
    btn = QPushButton(_btn_text(text, icon))
    btn.setStyleSheet(DANGER_BTN_QSS)
    return btn


def card_frame(radius: int = RADIUS.md) -> QFrame:
    """Painel/cartão padrão — fundo e borda seguem o tema via palette().

    Usa seletor por objectName (`#CardFrame`), não `QFrame{...}` — QLabel é
    subclasse de QFrame no Qt, então um seletor de tipo bare vazaria a borda/
    fundo do card para todo QLabel descendente (título de seção, ícone etc.).
    """
    frame = QFrame()
    frame.setObjectName("CardFrame")
    frame.setStyleSheet(
        f"#CardFrame{{background:palette(base);border:1px solid palette(mid);"
        f"border-radius:{radius}px;}}"
    )
    return frame


def section_label(text: str) -> QLabel:
    """Título de seção/aba — maior e mais forte que field_label()."""
    lbl = QLabel(text)
    style = TYPOGRAPHY.tab_title
    lbl.setStyleSheet(
        f"color:palette(text); font-size:{style.size}px; font-weight:{style.weight};"
    )
    return lbl


def admin_warning(message: str) -> QWidget:
    """Linha de aviso (ícone + texto, cor `warning`) para funcionalidades que
    exigem privilégio de Administrador (ex.: raw socket ICMP). Usado por
    Traceroute e MTR — ambos checam `core.network.is_admin()` e só mostram
    isto quando `False`; este widget não sabe nada sobre admin, só renderiza.
    """
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACING.xs)

    icon_lbl = QLabel()
    icon_lbl.setPixmap(qta.icon("fa5s.exclamation-triangle", color=DARK.warning).pixmap(_WARNING_ICON_PX))
    layout.addWidget(icon_lbl)

    text_lbl = QLabel(message)
    text_lbl.setStyleSheet(f"color:{DARK.warning}; font-size:11px;")
    layout.addWidget(text_lbl, 1)

    return row


_TOGGLE_LINK_QSS = (
    f"QPushButton{{color:{DARK.primary};font-size:11px;border:none;"
    f"background:transparent;text-align:left;padding:2px 0;}}"
    f"QPushButton:hover{{color:{DARK.primary_hover};text-decoration:underline;}}"
)


def toggle_link_button(text: str) -> QPushButton:
    """Botão flat, estilo link, checkable — para seções colapsáveis tipo
    "▸ Avançado". Quem chama conecta `toggled` e alterna o texto/visibilidade
    da seção; este builder só cuida da aparência."""
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setStyleSheet(_TOGGLE_LINK_QSS)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    return btn


def stat_card(label: str, value: str = "—", radius: int = RADIUS.sm) -> tuple[QFrame, QLabel]:
    """Card de métrica pequeno: valor grande em cima, rótulo embaixo. Retorna
    (frame, value_label) — quem chama guarda `value_label` para atualizar
    texto/cor depois via `.setText()`/`.setStyleSheet()`.
    """
    frame = card_frame(radius)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(SPACING.sm, SPACING.sm, SPACING.sm, SPACING.sm)
    layout.setSpacing(2)

    value_style = TYPOGRAPHY.value
    value_lbl = QLabel(value)
    value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    value_lbl.setStyleSheet(
        f"color:{DARK.text_muted}; font-size:{value_style.size}px; font-weight:{value_style.weight};"
    )
    layout.addWidget(value_lbl)

    label_style = TYPOGRAPHY.label
    label_lbl = QLabel(label)
    label_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label_lbl.setStyleSheet(
        f"color:{DARK.text_muted}; font-size:{label_style.size}px; letter-spacing:0.5px;"
    )
    layout.addWidget(label_lbl)

    return frame, value_lbl


def status_badge(status: HostStatus) -> QLabel:
    """Badge textual colorido para HostStatus (IDLE/RUNNING/UP/DOWN/ERROR)."""
    lbl = QLabel(STATUS_LABEL[status])
    color = STATUS_COLOR[status]
    lbl.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold;")
    return lbl


def count_badge(text: str, color: str) -> QLabel:
    """Pill pequeno com fundo colorido — para contadores em destaque (ex.:
    Up/Down na status bar), diferente de `status_badge()` (que é só texto
    colorido, sem fundo)."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{color}; color:{DARK.on_primary}; font-size:11px; font-weight:bold;"
        f"border-radius:{RADIUS.sm}px; padding:1px {SPACING.xs}px;"
    )
    return lbl
