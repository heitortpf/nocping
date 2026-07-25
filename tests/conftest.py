"""
tests/conftest.py
Fixtures compartilhadas pelos testes de UI (test_ui_navigation.py,
test_ui_theme.py). Não são autouse -- só os testes que constroem
MainWindow/MonitorTab de verdade precisam delas; o resto da suíte (core/,
_utils) não é afetado.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture
def isolate_hosts_persistence(monkeypatch):
    """MonitorTab.__init__ chama load_hosts() e _add_card_from_config()/
    _remove_card() chamam save_hosts() -- sem isolar isso, testes de UI
    leriam e sobrescreveriam o nocping_hosts.json real da máquina de quem
    roda a suíte. Substitui as referências já importadas em ui/monitor_tab.py
    (import por nome, então patchear core.config_store não bastaria)."""
    monkeypatch.setattr("ui.monitor_tab.load_hosts", lambda: [])
    monkeypatch.setattr("ui.monitor_tab.save_hosts", lambda cards: None)


@pytest.fixture
def clean_main_window_instances():
    """MainWindow._instances é uma lista de classe (compartilhada entre
    todas as instâncias/processo) e só é limpa organicamente dentro de
    _shutdown(), que roda via QApplication.aboutToQuit -- sinal que os
    testes não emitem. Sem isso, MainWindows de um teste vazariam pro
    _instances visto pelo próximo teste."""
    from ui.main_window import MainWindow
    before = list(MainWindow._instances)
    yield
    MainWindow._instances[:] = before
