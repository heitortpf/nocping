"""
tests/test_ui_theme.py
Alternar tema (claro/escuro) não deve lançar exceção e deve propagar pra
todas as MainWindow abertas (MainWindow._instances) e pros widgets internos
que MainWindow._toggle_theme() atualiza manualmente (QuickPingTab, e o
mini-gráfico de RTT de cada HostCard do Monitor) -- ver
MainWindow._toggle_theme() em ui/main_window.py.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from ui.main_window import MainWindow
from core.models import ProbeConfig, ProbeMode, IPVersion


@pytest.fixture
def main_window(qtbot, isolate_hosts_persistence, clean_main_window_instances):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    return win


def _tcp_cfg(host: str) -> ProbeConfig:
    return ProbeConfig(host=host, mode=ProbeMode.TCP, ip_version=IPVersion.AUTO)


# ---------------------------------------------------------------------------
# Não deve lançar exceção
# ---------------------------------------------------------------------------

def test_toggle_theme_does_not_raise(main_window):
    win = main_window
    win._toggle_theme()
    win._toggle_theme()  # ida e volta


def test_toggle_theme_with_real_host_card_does_not_raise(main_window):
    """Caminho completo, sem mocks: card real no Monitor, apply_theme() real
    do RttGraph incluso -- o cenário que a auditoria de performance já
    exercitou manualmente, agora fixado como teste automatizado."""
    win = main_window
    win._monitor._add_card_from_config(_tcp_cfg("10.0.0.2"))

    win._toggle_theme()
    win._toggle_theme()


def test_toggle_theme_flips_is_dark(main_window):
    win = main_window
    before = win._is_dark
    win._toggle_theme()
    assert win._is_dark is not before


# ---------------------------------------------------------------------------
# Propaga pra todas as janelas abertas (_instances)
# ---------------------------------------------------------------------------

def test_toggle_theme_updates_all_open_instances(
    qtbot, isolate_hosts_persistence, clean_main_window_instances
):
    win1 = MainWindow()
    win2 = MainWindow()
    qtbot.addWidget(win1)
    qtbot.addWidget(win2)
    win1.show()
    win2.show()

    assert win1 in MainWindow._instances
    assert win2 in MainWindow._instances

    before = win1._is_dark
    win1._toggle_theme()

    assert win1._is_dark != before
    assert win2._is_dark == win1._is_dark  # a segunda janela acompanha a primeira


def test_toggle_theme_updates_window_chrome_of_every_instance(
    qtbot, isolate_hosts_persistence, clean_main_window_instances, monkeypatch
):
    """_toggle_theme() chama _apply_window_theme() em CADA item de
    _instances, não só na janela onde o botão foi clicado."""
    win1 = MainWindow()
    win2 = MainWindow()
    qtbot.addWidget(win1)
    qtbot.addWidget(win2)

    calls = []
    monkeypatch.setattr(win1, "_apply_window_theme", lambda: calls.append(win1))
    monkeypatch.setattr(win2, "_apply_window_theme", lambda: calls.append(win2))

    win1._toggle_theme()

    assert win1 in calls
    assert win2 in calls


# ---------------------------------------------------------------------------
# Atualiza os widgets internos (QuickPingTab, gráficos de HostCard)
# ---------------------------------------------------------------------------

def test_toggle_theme_updates_quick_ping_panel(main_window, monkeypatch):
    win = main_window
    calls = []
    monkeypatch.setattr(win._quick_ping, "apply_theme", lambda dark: calls.append(dark))

    expected_new_dark = not win._is_dark
    win._toggle_theme()

    assert calls == [expected_new_dark]


def test_toggle_theme_updates_monitor_host_card_graph(main_window, monkeypatch):
    win = main_window
    win._monitor._add_card_from_config(_tcp_cfg("10.0.0.1"))
    card = win._monitor._cards[0]

    calls = []
    monkeypatch.setattr(card._graph, "apply_theme", lambda dark: calls.append(dark))

    expected_new_dark = not win._is_dark
    win._toggle_theme()

    assert calls == [expected_new_dark]


def test_toggle_theme_updates_every_card_when_multiple_hosts(main_window, monkeypatch):
    win = main_window
    for host in ("10.0.0.1", "10.0.0.2", "10.0.0.3"):
        win._monitor._add_card_from_config(_tcp_cfg(host))
    assert len(win._monitor._cards) == 3

    calls_per_card = []
    for card in win._monitor._cards:
        calls = []
        calls_per_card.append(calls)
        monkeypatch.setattr(card._graph, "apply_theme", lambda dark, c=calls: c.append(dark))

    win._toggle_theme()

    assert all(len(calls) == 1 for calls in calls_per_card)
