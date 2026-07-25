"""
tests/test_multi_window_close.py
Valida o fix do bug encontrado no QA da v2.0.0 (docs/QA_CHECKLIST_v2.md):
MainWindow.closeEvent() chamava QApplication.quit() incondicionalmente em
QUALQUER instância, então fechar uma janela secundária (aberta via Ctrl+N)
derrubava o app inteiro — inclusive a janela principal e os hosts sendo
monitorados nela.

Comportamento esperado agora: fechar uma janela só fecha aquela janela
(limpa os workers dela, sai de MainWindow._instances, some da bandeja); o
processo só encerra de verdade (QApplication.quit()) quando a ÚLTIMA janela
fecha. QApplication.quit() é mockado em vez de deixado rodar de verdade —
um app.exec() bloqueante travaria o test runner; o que importa pro teste é
a DECISÃO de chamar quit() ou não, não o encerramento real do processo
(isso foi verificado manualmente com um app.exec() de verdade durante o
desenvolvimento do fix).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from ui.main_window import MainWindow
from core.models import ProbeConfig, ProbeMode


@pytest.fixture
def two_windows(qtbot, isolate_hosts_persistence, clean_main_window_instances):
    win1 = MainWindow()
    win2 = MainWindow()
    qtbot.addWidget(win1)
    qtbot.addWidget(win2)
    win1.show()
    win2.show()
    return win1, win2


def test_closing_secondary_window_does_not_quit_app(two_windows, monkeypatch):
    win1, win2 = two_windows
    quit_calls = []
    monkeypatch.setattr("ui.main_window.QApplication.quit", lambda: quit_calls.append(1))

    win2.close()

    assert quit_calls == []


def test_closing_secondary_window_removes_only_itself_from_instances(two_windows):
    win1, win2 = two_windows

    win2.close()

    assert win2 not in MainWindow._instances
    assert win1 in MainWindow._instances


def test_closing_secondary_window_keeps_primary_visible_and_functional(two_windows):
    win1, win2 = two_windows

    win2.close()

    assert win1.isVisible()
    # "funcional" = ainda consegue operar normalmente -- adicionar e rodar
    # um host no Monitor da janela que continua aberta.
    win1._monitor._add_card_from_config(ProbeConfig(host="127.0.0.1", mode=ProbeMode.TCP))
    assert len(win1._monitor._cards) >= 1


def test_closing_secondary_window_hides_its_own_tray_icon(two_windows):
    win1, win2 = two_windows
    hide_calls = []
    win2._tray.hide = lambda: hide_calls.append(1)

    win2.close()

    assert hide_calls == [1]


def test_closing_secondary_window_cleans_up_its_own_workers(two_windows):
    win1, win2 = two_windows
    cleanup_calls = []
    win2._quick_ping.cleanup = lambda: cleanup_calls.append(1)

    win2.close()

    assert cleanup_calls == [1]


def test_closing_last_window_quits_app(qtbot, isolate_hosts_persistence, clean_main_window_instances, monkeypatch):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    quit_calls = []
    monkeypatch.setattr("ui.main_window.QApplication.quit", lambda: quit_calls.append(1))

    win.close()

    assert quit_calls == [1]
    assert win not in MainWindow._instances


def test_closing_two_windows_in_sequence_quits_only_on_the_second(two_windows, monkeypatch):
    win1, win2 = two_windows
    quit_calls = []
    monkeypatch.setattr("ui.main_window.QApplication.quit", lambda: quit_calls.append(1))

    win2.close()
    assert quit_calls == []

    win1.close()
    assert quit_calls == [1]
    assert MainWindow._instances == []


def test_cleanup_window_is_idempotent(two_windows):
    """closeEvent() chama _cleanup_window(); se o app realmente encerrar
    depois, _shutdown() chama de novo pra garantir que toda janela ainda
    aberta seja limpa -- pra janela que já se limpou sozinha, isso não pode
    repetir o trabalho (parar um worker já parado 2x, etc.)."""
    win1, _ = two_windows
    cleanup_calls = []
    win1._quick_ping.cleanup = lambda: cleanup_calls.append(1)

    win1._cleanup_window()
    win1._cleanup_window()

    assert cleanup_calls == [1]


def test_shutdown_cleans_all_remaining_windows(two_windows):
    """Simula o caminho que pula closeEvent inteiramente -- "Sair" no menu
    Arquivo ou no menu da bandeja chama QApplication.quit() direto, sem
    fechar as janelas uma a uma primeiro. aboutToQuit dispara _shutdown(),
    que precisa limpar TODAS as janelas ainda em _instances, não só self."""
    win1, win2 = two_windows
    calls = {"win1": [], "win2": []}
    win1._quick_ping.cleanup = lambda: calls["win1"].append(1)
    win2._quick_ping.cleanup = lambda: calls["win2"].append(1)

    win1._shutdown()

    assert calls["win1"] == [1]
    assert calls["win2"] == [1]
    assert MainWindow._instances == []


def test_shutdown_after_closeevent_does_not_duplicate_cleanup_on_last_window(
    qtbot, isolate_hosts_persistence, clean_main_window_instances, monkeypatch
):
    """A janela que efetivamente causa o quit (closeEvent -> _instances
    vazia -> QApplication.quit()) já rodou _cleanup_window() sozinha; se
    _shutdown() disparar depois (aboutToQuit real), não deve repetir a
    limpeza nela."""
    win = MainWindow()
    qtbot.addWidget(win)
    win.show()
    monkeypatch.setattr("ui.main_window.QApplication.quit", lambda: None)

    cleanup_calls = []
    win._quick_ping.cleanup = lambda: cleanup_calls.append(1)

    win.close()  # closeEvent -> _cleanup_window() (1ª vez) -> quit() mockado
    assert cleanup_calls == [1]

    win._shutdown()  # simula aboutToQuit disparando de verdade depois
    assert cleanup_calls == [1]  # não duplicou
