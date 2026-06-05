"""
NOCPing — ui/widgets/rtt_graph.py
Gráfico de RTT em tempo real usando pyqtgraph.
"""
from collections import deque

import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication
from ._utils import rtt_color


class RttGraph(pg.PlotWidget):
    MAX_POINTS = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history = deque([0.0] * self.MAX_POINTS, maxlen=self.MAX_POINTS)
        self._timeout_mask = deque([False] * self.MAX_POINTS, maxlen=self.MAX_POINTS)

        # Detecta tema atual na construção
        app = QApplication.instance()
        dark = True
        if app:
            win_color = app.palette().color(app.palette().ColorRole.Window)
            dark = win_color.lightness() < 128
        self._apply_colors(dark)

        self.setFixedHeight(70)
        self.hideAxis("bottom")
        self.showAxis("left")
        self.getAxis("left").setStyle(tickLength=3, tickTextOffset=2)
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.showGrid(y=True, alpha=0.15)

        self._curve = self.plot(
            list(range(self.MAX_POINTS)),
            list(self._history),
            pen=pg.mkPen("#4ade80", width=1.5),
            fillLevel=0,
            brush=pg.mkBrush("#4ade8018"),
        )
        self._scatter = pg.ScatterPlotItem(size=5, pen=None)
        self.addItem(self._scatter)

    def apply_theme(self, dark: bool):
        self._apply_colors(dark)
        self._redraw()

    def _apply_colors(self, dark: bool):
        bg   = "#1e1e2e" if dark else "#e6e9ef"
        tick = "#888"    if dark else "#555"
        self.setBackground(bg)
        self.getAxis("left").setTextPen(pg.mkPen(tick))

    def add_point(self, ms: float, timeout: bool = False):
        self._history.append(ms)
        self._timeout_mask.append(timeout)
        self._redraw()

    def _redraw(self):
        y = list(self._history)
        x = list(range(len(y)))

        # Cor da linha baseada na média dos últimos valores não-timeout
        valid = [v for v, t in zip(y, self._timeout_mask) if not t and v > 0]
        avg = sum(valid) / len(valid) if valid else 0

        color = "#6b7280" if avg <= 0 else rtt_color(avg)

        self._curve.setPen(pg.mkPen(color, width=1.5))
        self._curve.setBrush(pg.mkBrush(color + "18"))
        self._curve.setData(x, y)

        # Pontos vermelhos para timeouts
        timeout_x = [i for i, t in enumerate(self._timeout_mask) if t]
        timeout_y = [0.0] * len(timeout_x)
        self._scatter.setData(
            x=timeout_x, y=timeout_y,
            brush=pg.mkBrush("#f87171"),
            pen=None,
        )

        # Ajuste dinâmico do eixo Y
        mx = max(y) if any(v > 0 for v in y) else 100
        self.setYRange(0, mx * 1.2, padding=0)

    def reset(self):
        self._history = deque([0.0] * self.MAX_POINTS, maxlen=self.MAX_POINTS)
        self._timeout_mask = deque([False] * self.MAX_POINTS, maxlen=self.MAX_POINTS)
        self._redraw()
