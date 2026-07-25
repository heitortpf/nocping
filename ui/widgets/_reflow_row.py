"""
NOCPing — ui/widgets/_reflow_row.py
Uma linha de widgets "tipo toolbar" (grupo à esquerda, `addStretch()`,
grupo à direita empurrado pro fim) que quebra para duas linhas quando a
largura disponível não é suficiente pra mostrar tudo sem comprimir nada —
em vez de deixar o Qt cortar texto de botão/chip.

Por que não reaproveitar FlowLayout (ui/widgets/_flow_layout.py, usado pela
grade de HostCard do Monitor): FlowLayout quebra item a item e não tem
conceito de "empurrar pro fim" (`addStretch()`) — usá-lo aqui mudaria a
aparência da barra também em janelas largas (perderia o alinhamento à
direita dos botões de exportar), o que quebraria a regra de não regredir
nada em ~1100px+.

Usado em ui/scan_tab.py e ui/monitor_tab.py.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLayout


class ReflowRow(QWidget):
    def __init__(self, left: list, right: list, spacing: int = 6, parent=None):
        """`left`/`right` — cada item é um QWidget ou um int (espaçamento
        fixo em px, equivalente a `layout.addSpacing(n)`). `left` fica antes
        do stretch, `right` depois (empurrado pro fim da linha larga)."""
        super().__init__(parent)
        self._left = left
        self._right = right
        self._spacing = spacing
        self._narrow: bool | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(spacing)

        self._row1 = QHBoxLayout()
        self._row1.setSpacing(spacing)
        self._row2 = QHBoxLayout()
        self._row2.setSpacing(spacing)
        self._row2_widget = QWidget()
        self._row2_widget.setLayout(self._row2)

        outer.addLayout(self._row1)
        outer.addWidget(self._row2_widget)

        self._set_wide()
        # Largura mínima pra caber tudo numa linha só, com o stretch no
        # tamanho mínimo dele — abaixo disso, quebra pra duas linhas.
        self._needed_width = self._row1.sizeHint().width()

    # ------------------------------------------------------------------

    @staticmethod
    def _clear(layout: QLayout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)  # solta do layout sem deletar o widget

    def _add_items(self, layout: QHBoxLayout, items: list):
        for item in items:
            if isinstance(item, int):
                layout.addSpacing(item)
            else:
                layout.addWidget(item)

    def _set_wide(self):
        if self._narrow is False:
            return
        self._narrow = False
        self._clear(self._row1)
        self._clear(self._row2)
        self._add_items(self._row1, self._left)
        self._row1.addStretch()
        self._add_items(self._row1, self._right)
        self._row2_widget.setVisible(False)

    def _set_narrow(self):
        if self._narrow is True:
            return
        self._narrow = True
        self._clear(self._row1)
        self._clear(self._row2)
        self._add_items(self._row1, self._left)
        self._row1.addStretch()
        self._add_items(self._row2, self._right)
        self._row2.addStretch()
        self._row2_widget.setVisible(True)

    # ------------------------------------------------------------------

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.size().width() < self._needed_width:
            self._set_narrow()
        else:
            self._set_wide()
