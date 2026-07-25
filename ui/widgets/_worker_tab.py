"""
NOCPing — ui/widgets/_worker_tab.py
Mixin para abas com um QThread worker de execução única (Scan, Banner,
Traceroute, MTR): padroniza o desligamento seguro do worker (desconectar
sinais, sinalizar parada, aguardar e agendar deleteLater()).

As quatro abas reimplementavam essa lógica de forma quase idêntica, mas com
pequenas divergências entre si (timeout de espera, se checam isRunning()
antes de parar, `stop()` vs `requestInterruption()`). O mixin preserva cada
divergência via os hooks abaixo — a intenção é eliminar a duplicação de
estrutura, não unificar comportamento que já era diferente entre as abas.
"""


class WorkerTabMixin:
    _WORKER_WAIT_MS: int = 2000
    _WORKER_WAIT_GUARDED: bool = True  # só para/espera se worker.isRunning()

    def _worker_signal_pairs(self) -> list[tuple[str, str]]:
        """[(nome do sinal, nome do slot), ...] na ordem original de disconnect."""
        raise NotImplementedError

    def _stop_worker(self):
        """Como sinalizar a parada do worker. Default: worker.stop()."""
        self._worker.stop()

    def _cleanup_worker(self):
        if self._worker is None:
            return
        try:
            for signal_name, slot_name in self._worker_signal_pairs():
                getattr(self._worker, signal_name).disconnect(getattr(self, slot_name))
        except RuntimeError:
            pass
        if self._WORKER_WAIT_GUARDED:
            if self._worker.isRunning():
                self._stop_worker()
                self._worker.wait(self._WORKER_WAIT_MS)
        else:
            self._stop_worker()
            self._worker.wait(self._WORKER_WAIT_MS)
        self._worker.deleteLater()
        self._worker = None
