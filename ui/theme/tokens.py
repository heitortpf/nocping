"""
NOCPing — ui/theme/tokens.py
Fonte única de verdade para cores, espaçamento, raio de borda e tipografia.

Nenhum outro módulo deve declarar cores hex literais para UI de aplicação —
sempre importar `DARK`/`LIGHT` (ou `tokens_for(dark)`) daqui. Os valores abaixo
foram extraídos 1:1 do que já existia hardcoded em ui/main_window.py e
ui/widgets/_utils.py antes desta refatoração (ver docs/baseline/hex-colors.txt
e docs/DESIGN_SYSTEM.md) — a intenção desta etapa é centralizar, não mudar
a aparência do app. Alguns campos guardam valores que coincidem entre temas
ou entre si (ex.: `pane_border` claro == `border`, mas escuro == `button_bg`)
porque essa era a mistura original em ui/main_window.py; a inconsistência é
documentada em docs/DESIGN_SYSTEM.md em vez de "corrigida" silenciosamente.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ColorTokens:
    # Superfícies (equivalem aos QPalette.ColorRole usados em apply_theme)
    bg: str                  # Window — fundo da janela
    surface: str             # Base — fundo de inputs/tabelas/cards no tema claro
    surface_elevated: str    # AlternateBase — menus, tabs inativas, scrollbar track
    field_bg: str            # fundo de QLineEdit/QComboBox (difere de `surface` no escuro)
    button_bg: str           # Button role — botões padrão do Qt, item hover de menu
    control_bg: str          # fundo das setas do QSpinBox
    control_hover: str
    control_press: str
    pane_border: str         # borda do QTabWidget::pane

    border: str              # Mid — bordas de campos, divisores, scrollbar handle
    text_primary: str        # Text/WindowText/ButtonText
    text_secondary: str      # PlaceholderText
    text_muted: str          # cinza invariante usado em rótulos de campo/status bar (legado)
    tab_fg_inactive: str     # cor da aba não selecionada (legado, invariante nos 2 temas)
    link: str                # Link
    on_primary: str          # cor de texto sobre fundo `primary`/`danger_strong` (branco)

    # Marca / interação primária
    primary: str
    primary_hover: str
    primary_press: str

    # Semânticas de status (hoje idênticas nos dois temas — mantidas por tema
    # para permitir divergência futura sem migração de schema)
    success: str
    warning: str
    danger: str
    danger_strong: str        # vermelho sólido para botões destrutivos
    danger_strong_hover: str
    info: str                  # lilás usado em estados "em execução/iniciando"

    tooltip_bg: str
    tooltip_fg: str


DARK = ColorTokens(
    bg="#11111b",
    surface="#181825",
    surface_elevated="#1e1e2e",
    field_bg="#313244",
    button_bg="#313244",
    control_bg="#45475a",
    control_hover="#585b70",
    control_press="#6c7086",
    pane_border="#313244",

    border="#45475a",
    text_primary="#cdd6f4",
    text_secondary="#6b7280",
    text_muted="#6b7280",
    tab_fg_inactive="#9ca3af",
    link="#89b4fa",
    on_primary="#ffffff",

    primary="#7c3aed",
    primary_hover="#6d28d9",
    primary_press="#5b21b6",

    success="#4ade80",
    warning="#facc15",
    danger="#f87171",
    danger_strong="#dc2626",
    danger_strong_hover="#b91c1c",
    info="#a78bfa",

    tooltip_bg="#313244",
    tooltip_fg="#cdd6f4",
)

LIGHT = ColorTokens(
    bg="#eff1f5",
    surface="#ffffff",
    surface_elevated="#e6e9ef",
    field_bg="#ffffff",
    button_bg="#dce0e8",
    control_bg="#dce0e8",
    control_hover="#c8ccd4",
    control_press="#bcc0cc",
    pane_border="#bcc0cc",

    border="#bcc0cc",
    text_primary="#4c4f69",
    text_secondary="#9ca3af",
    text_muted="#6b7280",
    tab_fg_inactive="#9ca3af",
    link="#1d4ed8",
    on_primary="#ffffff",

    primary="#7c3aed",
    primary_hover="#6d28d9",
    primary_press="#5b21b6",

    success="#4ade80",
    warning="#facc15",
    danger="#f87171",
    danger_strong="#dc2626",
    danger_strong_hover="#b91c1c",
    info="#a78bfa",

    tooltip_bg="#dce0e8",
    tooltip_fg="#4c4f69",
)


def tokens_for(dark: bool) -> ColorTokens:
    return DARK if dark else LIGHT


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32


@dataclass(frozen=True)
class Radius:
    sm: int = 6
    md: int = 10
    lg: int = 16


@dataclass(frozen=True)
class TypeStyle:
    size: int
    weight: int  # equivalente informal a QFont.Weight (400 normal, 600 demibold, 700 bold)


@dataclass(frozen=True)
class Typography:
    tab_title: TypeStyle    # título de aba / cabeçalho de seção
    label: TypeStyle        # rótulo pequeno de campo (ex.: "HOST / IP")
    value: TypeStyle        # valor em destaque (ex.: RTT atual)
    body: TypeStyle         # texto de corpo / tabela / log
    hero: TypeStyle         # métrica hero de card (ex.: RTT atual do HostCard)


SPACING = Spacing()
RADIUS = Radius()
TYPOGRAPHY = Typography(
    tab_title=TypeStyle(size=14, weight=700),
    label=TypeStyle(size=10, weight=500),
    value=TypeStyle(size=18, weight=700),
    body=TypeStyle(size=12, weight=400),
    hero=TypeStyle(size=26, weight=700),
)
