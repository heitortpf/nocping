"""
tests/test_taskbar_icon.py
`ui.main_window._force_native_taskbar_icon()` -- fix de troubleshooting real
(ver CLAUDE.md, seção "Barra de tarefas: WM_SETICON direto"): numa instalação
Windows específica, nem `app.setWindowIcon()` nem `self.setWindowIcon()`
faziam o ícone da janela rodando aparecer certo na barra de tarefas, mesmo
com o `.ico` e o recurso do `.exe` corretos. `WM_SETICON` via ctypes é o
mecanismo de mais baixo nível pra isso e contornou o problema.

`ctypes.windll` só existe de verdade no Windows -- os testes usam
`monkeypatch.setattr(ctypes, "windll", fake, raising=False)` pra simular a
API em qualquer plataforma que rode a suíte (CI cobre Windows/Linux/macOS).
"""
import ctypes
import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ui import main_window as main_window_module


def test_force_native_taskbar_icon_noop_on_non_windows(monkeypatch):
    monkeypatch.setattr(main_window_module.sys, "platform", "linux")
    win = MagicMock()
    main_window_module._force_native_taskbar_icon(win)
    win.winId.assert_not_called()


def test_force_native_taskbar_icon_noop_if_ico_missing(monkeypatch):
    monkeypatch.setattr(main_window_module.sys, "platform", "win32")
    monkeypatch.setattr(main_window_module.os.path, "exists", lambda p: False)
    win = MagicMock()
    main_window_module._force_native_taskbar_icon(win)
    win.winId.assert_not_called()


def test_force_native_taskbar_icon_calls_wm_seticon_on_windows(monkeypatch):
    monkeypatch.setattr(main_window_module.sys, "platform", "win32")
    monkeypatch.setattr(main_window_module.os.path, "exists", lambda p: True)

    fake_user32 = MagicMock()
    fake_user32.LoadImageW.return_value = 999  # HICON não-nulo
    fake_windll = MagicMock(user32=fake_user32)
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)

    win = MagicMock()
    win.winId.return_value = 12345

    main_window_module._force_native_taskbar_icon(win)

    assert fake_user32.LoadImageW.call_count == 2  # ICON_SMALL + ICON_BIG
    assert fake_user32.SendMessageW.call_count == 2
    wm_seticon_calls = [c.args[1] for c in fake_user32.SendMessageW.call_args_list]
    assert all(code == 0x0080 for code in wm_seticon_calls)  # WM_SETICON


def test_force_native_taskbar_icon_swallows_exceptions(monkeypatch):
    monkeypatch.setattr(main_window_module.sys, "platform", "win32")
    monkeypatch.setattr(main_window_module.os.path, "exists", lambda p: True)

    win = MagicMock()
    win.winId.side_effect = RuntimeError("sem HWND nativo ainda")

    main_window_module._force_native_taskbar_icon(win)  # não deve levantar


def test_force_native_taskbar_icon_skips_seticon_when_load_fails(monkeypatch):
    monkeypatch.setattr(main_window_module.sys, "platform", "win32")
    monkeypatch.setattr(main_window_module.os.path, "exists", lambda p: True)

    fake_user32 = MagicMock()
    fake_user32.LoadImageW.return_value = 0  # falha ao carregar o ícone
    fake_windll = MagicMock(user32=fake_user32)
    monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)

    win = MagicMock()
    win.winId.return_value = 12345

    main_window_module._force_native_taskbar_icon(win)

    fake_user32.SendMessageW.assert_not_called()
