"""
NOCPing — ui/widgets/quick_ping_graph_panel.py
Gráfico RTT expandido do Quick Ping — moldura + título + RttGraph.

Extraído de ui/quick_ping_tab.py. A construção do RttGraph (import de
pyqtgraph, ~200ms na primeira vez) continua adiada via QTimer.singleShot(0, ...)
para depois do primeiro paint da janela, exatamente como antes — Quick Ping é
a aba inicial construída eagerly, então esse adiamento evita pagar o custo do
import antes de window.show().
"""
from PyQt6 import sip
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget, QLabel, QSizePolicy
from PyQt6.QtCore import QTimer


class QuickPingGraphPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("QPGraphFrame")
        self.setStyleSheet("""
            #QPGraphFrame {
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: 8px;
            }
        """)
        self._graph = None
        self._build_ui()
        QTimer.singleShot(0, self._init_graph)

    def _build_ui(self):
        inner = QVBoxLayout(self)
        inner.setContentsMargins(10, 8, 10, 8)
        inner.setSpacing(4)
        self._inner = inner

        title = QLabel("RTT em Tempo Real")
        title.setStyleSheet(
            "color:palette(text); font-size:11px; font-weight:bold; letter-spacing:0.5px;"
        )
        inner.addWidget(title)

        self._placeholder = QWidget()
        inner.addWidget(self._placeholder, 1)

    def _init_graph(self):
        """Constrói o RttGraph (import de pyqtgraph incluso) após o primeiro paint."""
        if self._graph is not None:
            return
        # QTimer.singleShot(0, ...) agendado no __init__ só dispara no
        # próximo tick do event loop -- se a janela fechar/for destruída
        # antes disso (ex.: teste que cria e fecha a janela sem dar tempo
        # pro tick rodar), os objetos C++ por trás de self/self._inner já
        # podem ter sido deletados quando este callback finalmente roda.
        # Achado via CI (Windows/macOS/Linux) no QA da v2.0.0 -- não
        # reproduzia localmente por timing, mas é alcançável em uso real
        # também (ex.: fechar a janela muito rápido após Ctrl+N).
        #
        # sip.isdeleted(self) sozinho NÃO é suficiente: em CI observamos
        # self._inner (QVBoxLayout, filho de self) já deletado enquanto
        # sip.isdeleted(self) ainda reportava False -- a ordem de
        # destruição dos objetos internos do Qt não é atômica o bastante
        # pra confiar numa checagem só do widget pai. O try/except é o
        # jeito correto de cobrir isso: qualquer uso de um objeto PyQt já
        # deletado no lado C++ levanta RuntimeError, não importa qual
        # objeto especificamente já foi destruído.
        if sip.isdeleted(self):
            return
        try:
            from .rtt_graph import RttGraph
            graph = RttGraph()
            graph.MAX_POINTS = 120
            graph.reset()
            graph.setMinimumHeight(140)
            graph.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._inner.replaceWidget(self._placeholder, graph)
        except RuntimeError:
            return
        self._graph = graph
        self._placeholder.deleteLater()
        self._placeholder = None

    # ------------------------------------------------------------------
    # API pública (usada pelo orquestrador QuickPingTab)
    # ------------------------------------------------------------------

    def reset(self):
        if self._graph is None:
            self._init_graph()
        # _init_graph() pode não conseguir construir o gráfico (widget já
        # deletado, ver comentário lá) e deixar self._graph None -- nesse
        # caso não há nada mais pra resetar.
        if self._graph is not None:
            self._graph.reset()

    def add_point(self, ms: float, timeout: bool):
        if self._graph is not None:
            self._graph.add_point(ms, timeout)

    def apply_theme(self, dark: bool):
        if self._graph is not None:
            self._graph.apply_theme(dark)
