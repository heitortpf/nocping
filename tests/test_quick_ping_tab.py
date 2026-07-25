"""
tests/test_quick_ping_tab.py
Valida a paridade de notificação Quick Ping vs Monitor decidida no QA da
v2.0.0 (docs/QA_CHECKLIST_v2.md): antes, QuickPingTab só emitia
host_status_changed em transições UP/DOWN (via _on_result), nunca em ERROR
(via _on_error) — diferente de HostCard, que trata ERROR como qualquer
outra transição de status. Reaproveita o mesmo sinal/fluxo existente
(host_status_changed), sem mecanismo de notificação paralelo.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PyQt6.QtCore import Qt

from core.models import HostStatus, IPVersion, ProbeConfig, ProbeMode
from core.network import is_admin
from ui.quick_ping_tab import QuickPingTab


@pytest.fixture
def qp(qtbot):
    tab = QuickPingTab()
    qtbot.addWidget(tab)
    return tab


def test_on_error_emits_host_status_changed_with_error(qp, qtbot):
    qp._control._inp_host.setText("8.8.8.8")

    with qtbot.waitSignal(qp.host_status_changed, timeout=1000) as blocker:
        qp._on_error("Modo ICMP requer privilégios de Administrador.")

    host, old, new = blocker.args
    assert host == "8.8.8.8"
    assert new == HostStatus.ERROR


def test_on_error_notifies_even_as_first_observation(qp, qtbot):
    """Diferente de _on_result() (que suprime a primeira leitura como
    linha de base), um erro deve notificar mesmo sendo a primeira coisa
    que acontece na sessão -- é exatamente o caso real (ICMP/UDP sem
    admin falha antes de qualquer PingResult existir)."""
    assert getattr(qp, "_last_status", None) is None

    calls = []
    qp.host_status_changed.connect(lambda h, o, n: calls.append((h, o, n)))
    qp._on_error("erro qualquer")

    assert len(calls) == 1
    assert calls[0][2] == HostStatus.ERROR


def test_on_error_does_not_duplicate_notification_if_called_again(qp):
    calls = []
    qp.host_status_changed.connect(lambda h, o, n: calls.append(n))

    qp._on_error("primeiro erro")
    qp._on_error("segundo erro, mesmo estado")

    assert calls == [HostStatus.ERROR]


def test_on_error_updates_last_status_for_consistency(qp):
    qp._on_error("erro qualquer")
    assert qp._last_status == HostStatus.ERROR


@pytest.mark.skipif(is_admin(), reason="teste depende de rodar SEM admin (replica o cenário real do bug)")
def test_real_pingworker_icmp_without_admin_notifies_error_end_to_end(qp, qtbot):
    """Fim a fim, sem mocks: PingWorker real em modo ICMP sem admin emite
    error() de verdade (core/workers.py:62-66) -- confirma que o sinal
    chega em QuickPingTab.host_status_changed com HostStatus.ERROR pelo
    caminho real (_start_ping -> PingWorker -> _on_error), não só a
    chamada direta e isolada dos testes acima."""
    qp._control._inp_host.setText("127.0.0.1")
    idx = qp._control._cmb_mode.findData(ProbeMode.ICMP)
    qp._control._cmb_mode.setCurrentIndex(idx)

    with qtbot.waitSignal(qp.host_status_changed, timeout=5000) as blocker:
        qp._control.ping_requested.emit()

    host, old, new = blocker.args
    assert host == "127.0.0.1"
    assert new == HostStatus.ERROR

    qp._stop()
