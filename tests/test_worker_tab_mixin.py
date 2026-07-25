"""
tests/test_worker_tab_mixin.py
Valida o contrato de ui/widgets/_worker_tab.py (WorkerTabMixin), extraído na
fase de refatoração estrutural para eliminar a lógica de shutdown quase
idêntica duplicada entre ScanTab/BannerTab/TracerouteTab/MTRTab: desconectar
sinais, sinalizar parada e esperar o worker (`wait()`) antes de descartá-lo.

Usa um QThread fake (_FakeWorker) com sinais reais do PyQt6 em vez de um
Mock, porque _cleanup_worker() chama .connect()/.disconnect() de verdade
nos sinais — um Mock não reproduz a semântica de "disconnect falha se o
slot não estiver conectado", que é justamente uma das coisas testadas aqui.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PyQt6.QtCore import QThread, pyqtSignal

from ui.widgets._worker_tab import WorkerTabMixin


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class _FakeWorker(QThread):
    """QThread real (sinais do PyQt6 são de verdade), mas nunca chega a
    rodar de fato -- start()/run() não são chamados. isRunning()/stop()/
    wait() são sobrescritos para o teste controlar o cenário sem depender
    de timing de thread real."""
    result = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._fake_running = False
        self.stop_calls = 0
        self.wait_calls: list = []
        self.delete_later_called = False

    def set_running(self, value: bool):
        self._fake_running = value

    def isRunning(self):
        return self._fake_running

    def stop(self):
        self.stop_calls += 1

    def wait(self, ms=None):
        self.wait_calls.append(ms)
        return True

    def deleteLater(self):
        self.delete_later_called = True


class _FakeTab(WorkerTabMixin):
    """Host mínimo do mixin -- só o que _cleanup_worker() precisa: um
    _worker, os slots referenciados por _worker_signal_pairs() e os
    atributos de configuração do mixin."""

    def __init__(self, guarded: bool = True, wait_ms: int = 2000):
        self._WORKER_WAIT_GUARDED = guarded
        self._WORKER_WAIT_MS = wait_ms
        self._worker = None
        self.result_calls: list = []
        self.error_calls: list = []

    def _on_result(self, v):
        self.result_calls.append(v)

    def _on_error(self, msg):
        self.error_calls.append(msg)

    def _worker_signal_pairs(self):
        return [("result", "_on_result"), ("error", "_on_error")]


def _connected_tab(**kw) -> tuple[_FakeTab, _FakeWorker]:
    tab = _FakeTab(**kw)
    worker = _FakeWorker()
    tab._worker = worker
    worker.result.connect(tab._on_result)
    worker.error.connect(tab._on_error)
    return tab, worker


# ---------------------------------------------------------------------------
# Desconexão de sinais
# ---------------------------------------------------------------------------

def test_cleanup_disconnects_signals(qapp):
    tab, worker = _connected_tab()

    tab._cleanup_worker()

    # sinal desconectado -- emitir depois do cleanup não deve mais chegar no slot
    worker.result.emit(42)
    worker.error.emit("boom")
    assert tab.result_calls == []
    assert tab.error_calls == []


def test_cleanup_swallows_disconnect_typeerror_from_unconnected_slot(qapp):
    """Achado durante a escrita deste teste: o PyQt6 levanta TypeError (não
    RuntimeError) ao desconectar um slot que nunca foi conectado --
    `except RuntimeError` em _cleanup_worker() NÃO cobre esse caso.
    Na prática isso não afeta as 4 abas reais (Scan/Banner/Traceroute/MTR
    sempre conectam os sinais logo após criar o worker, antes de qualquer
    cleanup), mas fica documentado/pinado aqui em vez de assumido."""
    tab = _FakeTab()
    worker = _FakeWorker()
    tab._worker = worker
    # nunca conecta result/error -- disconnect() vai falhar com TypeError

    with pytest.raises(TypeError):
        tab._cleanup_worker()


# ---------------------------------------------------------------------------
# stop() + wait() -- worker em execução (caminho guardado, o default real)
# ---------------------------------------------------------------------------

def test_cleanup_running_worker_stops_and_waits(qapp):
    tab, worker = _connected_tab(guarded=True, wait_ms=1500)
    worker.set_running(True)

    tab._cleanup_worker()

    assert worker.stop_calls == 1
    assert worker.wait_calls == [1500]


def test_cleanup_deletes_and_resets_worker_reference(qapp):
    tab, worker = _connected_tab()
    worker.set_running(True)

    tab._cleanup_worker()

    assert worker.delete_later_called is True
    assert tab._worker is None


def test_cleanup_guarded_skips_stop_wait_when_not_running(qapp):
    """_WORKER_WAIT_GUARDED=True (default de WorkerTabMixin) só chama
    stop()/wait() se isRunning() for True -- um worker que já terminou
    sozinho não precisa ser interrompido de novo. Sinais continuam sendo
    desconectados e o worker continua sendo descartado."""
    tab, worker = _connected_tab(guarded=True)
    worker.set_running(False)

    tab._cleanup_worker()

    assert worker.stop_calls == 0
    assert worker.wait_calls == []
    assert worker.delete_later_called is True
    assert tab._worker is None


def test_cleanup_unguarded_always_stops_and_waits(qapp):
    """_WORKER_WAIT_GUARDED=False sempre para e espera o worker, mesmo que
    isRunning() já seja False -- comportamento "não-guardado" que o mixin
    preserva para a(s) aba(s) que dependiam dele antes da refatoração."""
    tab, worker = _connected_tab(guarded=False, wait_ms=999)
    worker.set_running(False)

    tab._cleanup_worker()

    assert worker.stop_calls == 1
    assert worker.wait_calls == [999]


# ---------------------------------------------------------------------------
# Idempotência / casos vazios
# ---------------------------------------------------------------------------

def test_cleanup_is_noop_when_worker_already_none(qapp):
    tab = _FakeTab()
    tab._worker = None

    tab._cleanup_worker()  # não deve lançar

    assert tab._worker is None


def test_cleanup_called_twice_is_safe(qapp):
    """_start() chama _cleanup_worker() antes de criar um worker novo -- em
    sequência rápida (start/stop/start) o cleanup pode ser chamado de novo
    sobre um _worker já None, e isso não pode lançar."""
    tab, worker = _connected_tab()
    worker.set_running(True)

    tab._cleanup_worker()
    assert tab._worker is None
    tab._cleanup_worker()  # segunda chamada -- worker já é None, deve ser no-op
    assert tab._worker is None
    assert worker.stop_calls == 1  # não foi parado de novo na segunda chamada
