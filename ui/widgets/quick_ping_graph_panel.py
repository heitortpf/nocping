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
        # pro tick rodar), self._inner (QVBoxLayout) já foi deletado no
        # lado C++ e replaceWidget() abaixo lançaria RuntimeError. Achado
        # via CI (Windows/macOS) no QA da v2.0.0 -- não reproduzia
        # localmente por timing, mas é alcançável em uso real também
        # (ex.: fechar a janela muito rápido após Ctrl+N).
        if sip.isdeleted(self):
            return
        from .rtt_graph import RttGraph
        self._graph = RttGraph()
        self._graph.MAX_POINTS = 120
        self._graph.reset()
        self._graph.setMinimumHeight(140)
        self._graph.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._inner.replaceWidget(self._placeholder, self._graph)
        self._placeholder.deleteLater()
        self._placeholder = None

    # ------------------------------------------------------------------
    # API pública (usada pelo orquestrador QuickPingTab)
    # ------------------------------------------------------------------

    def reset(self):
        if self._graph is None:
            self._init_graph()
        self._graph.reset()

    def add_point(self, ms: float, timeout: bool):
        self._graph.add_point(ms, timeout)

    def apply_theme(self, dark: bool):
        if self._graph is not None:
            self._graph.apply_theme(dark)
