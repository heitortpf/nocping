"""
tests/test_ui_navigation.py
Testa a sidebar de navegação (ui/widgets/sidebar.py + NavSidebar) e o
lazy-loading das abas Scan/Banner/Traceroute/MTR em
MainWindow._on_tab_activated() (ui/main_window.py) -- essas 4 abas só devem
ser construídas (__init__ real) no primeiro clique/ativação, nunca antes e
nunca de novo depois.

Usa pytest-qt (qtbot) para simular cliques reais nos botões da sidebar, em
vez de chamar os slots internos diretamente -- exercita o mesmo caminho que
o usuário real percorre (clique → NavSidebar.clicked → page_changed →
MainWindow._on_tab_activated).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow
from ui.scan_tab import ScanTab
from ui.banner_tab import BannerTab
from ui.traceroute_tab import TracerouteTab
from ui.mtr_tab import MTRTab


# (índice na sidebar/SECTIONS, nome usado por show_section(), classe lazy)
_LAZY_SECTIONS = [
    (2, "port_scan",  ScanTab),
    (3, "banner_tls", BannerTab),
    (4, "traceroute", TracerouteTab),
    (5, "mtr",        MTRTab),
]
_LAZY_IDS = [name for _, name, _ in _LAZY_SECTIONS]


@pytest.fixture
def main_window(qtbot, isolate_hosts_persistence, clean_main_window_instances):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    return win


# ---------------------------------------------------------------------------
# Troca de painel
# ---------------------------------------------------------------------------

def test_starts_on_quick_ping(main_window):
    win = main_window
    assert win._stack.currentIndex() == 0
    assert win._stack.currentWidget() is win._quick_ping
    assert win._sidebar._buttons[0].isChecked()


def test_sidebar_click_switches_stack_panel(main_window, qtbot):
    win = main_window

    qtbot.mouseClick(win._sidebar._buttons[1], Qt.MouseButton.LeftButton)
    assert win._stack.currentIndex() == 1
    assert win._stack.currentWidget() is win._monitor
    assert win._sidebar._buttons[1].isChecked()

    qtbot.mouseClick(win._sidebar._buttons[0], Qt.MouseButton.LeftButton)
    assert win._stack.currentIndex() == 0
    assert win._stack.currentWidget() is win._quick_ping


def test_show_section_syncs_sidebar_and_stack(main_window):
    win = main_window
    win.show_section("mtr")

    assert win._stack.currentIndex() == 5
    assert win._sidebar._buttons[5].isChecked()
    assert win._stack.currentWidget() is win._mtr


def test_show_section_accepts_all_declared_sections(main_window):
    win = main_window
    for i, name in enumerate(MainWindow.SECTIONS):
        win.show_section(name)
        assert win._stack.currentIndex() == i


# ---------------------------------------------------------------------------
# Abas eager (Quick Ping, Monitor) já existem na construção
# ---------------------------------------------------------------------------

def test_eager_tabs_initialized_at_construction(main_window):
    win = main_window
    assert win._initialized_tabs == {0, 1}
    assert win._scan is None
    assert win._banner is None
    assert win._traceroute is None
    assert win._mtr is None


# ---------------------------------------------------------------------------
# Lazy-loading: Scan/Banner/Traceroute/MTR só constroem no primeiro clique
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("index,section_name,cls", _LAZY_SECTIONS, ids=_LAZY_IDS)
def test_lazy_tab_not_constructed_before_activation(
    main_window, monkeypatch, index, section_name, cls
):
    calls = []
    monkeypatch.setattr(cls, "__init__", _spy(cls.__init__, calls))

    win = main_window  # abas lazy (índice 2-5) são placeholders até o 1º clique

    assert index not in win._initialized_tabs
    assert calls == []
    assert isinstance(win._stack.widget(index), cls) is False


@pytest.mark.parametrize("index,section_name,cls", _LAZY_SECTIONS, ids=_LAZY_IDS)
def test_lazy_tab_constructs_exactly_once_on_first_click(
    main_window, qtbot, monkeypatch, index, section_name, cls
):
    calls = []
    monkeypatch.setattr(cls, "__init__", _spy(cls.__init__, calls))

    win = main_window

    qtbot.mouseClick(win._sidebar._buttons[index], Qt.MouseButton.LeftButton)

    assert len(calls) == 1
    assert index in win._initialized_tabs
    assert isinstance(win._stack.currentWidget(), cls)


@pytest.mark.parametrize("index,section_name,cls", _LAZY_SECTIONS, ids=_LAZY_IDS)
def test_lazy_tab_does_not_reconstruct_on_repeated_activation(
    main_window, qtbot, monkeypatch, index, section_name, cls
):
    calls = []
    monkeypatch.setattr(cls, "__init__", _spy(cls.__init__, calls))

    win = main_window

    qtbot.mouseClick(win._sidebar._buttons[index], Qt.MouseButton.LeftButton)
    assert len(calls) == 1
    first_instance = win._stack.currentWidget()

    # clica de novo na mesma aba, navega pra outra e volta, e usa
    # show_section() -- nenhum desses caminhos deve reconstruir
    qtbot.mouseClick(win._sidebar._buttons[index], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(win._sidebar._buttons[0], Qt.MouseButton.LeftButton)
    qtbot.mouseClick(win._sidebar._buttons[index], Qt.MouseButton.LeftButton)
    win.show_section(section_name)

    assert len(calls) == 1
    assert win._stack.currentWidget() is first_instance


def _spy(original_init, calls: list):
    def spy_init(self, *args, **kwargs):
        calls.append(1)
        original_init(self, *args, **kwargs)
    return spy_init
