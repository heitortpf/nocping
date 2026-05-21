import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(scope="session")
def utils():
    from ui.widgets import _utils
    return _utils


# Tabela paramétrica: (ms, cor esperada)
@pytest.mark.parametrize("ms,expected", [
    (-10.0, "#f87171"),   # negativo → vermelho (timeout)
    (0.0,   "#f87171"),   # zero     → vermelho (timeout)
    (1.0,   "#4ade80"),   # rápido   → verde
    (49.9,  "#4ade80"),   # abaixo de 50 → verde
    (50.0,  "#facc15"),   # exato 50 → amarelo (fronteira inclusive)
    (149.9, "#facc15"),   # abaixo de 150 → amarelo
    (150.0, "#f87171"),   # exato 150 → vermelho (fronteira inclusive)
    (500.0, "#f87171"),   # alto     → vermelho
])
def test_rtt_color(utils, ms, expected):
    assert utils.rtt_color(ms) == expected, f"rtt_color({ms}) esperado {expected}"


def test_rtt_color_returns_valid_hex(utils):
    for ms in [-1, 0, 25, 49.9, 50, 100, 149.9, 150, 300]:
        color = utils.rtt_color(ms)
        assert color.startswith("#"), f"cor inválida para ms={ms}: {color!r}"
        assert len(color) == 7, f"hex deve ter 7 chars: {color!r}"


def test_rtt_color_is_pure_function(utils):
    assert utils.rtt_color(30) == utils.rtt_color(30)
    assert utils.rtt_color(100) == utils.rtt_color(100)


def test_primary_btn_style_contains_qss_selector(utils):
    assert "QPushButton" in utils.PRIMARY_BTN_STYLE
    assert "#7c3aed" in utils.PRIMARY_BTN_STYLE
    assert "hover" in utils.PRIMARY_BTN_STYLE
    assert "pressed" in utils.PRIMARY_BTN_STYLE


def test_table_style_uses_palette_not_hex(utils):
    assert "QTableWidget" in utils.TABLE_STYLE
    assert "palette(" in utils.TABLE_STYLE
    # não deve ter hex hardcoded de fundo
    import re
    bg_hex = re.findall(r"background\s*:\s*#[0-9a-fA-F]{6}", utils.TABLE_STYLE)
    assert bg_hex == [], f"TABLE_STYLE tem cor hex hardcoded: {bg_hex}"


def test_field_label_text():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from ui.widgets._utils import field_label
    lbl = field_label("PORTA")
    assert lbl.text() == "PORTA"
    assert "6b7280" in lbl.styleSheet()
