"""
NOCPing — ui/scan_tab.py
Aba de port scan multithread.

Redesenhada para usar o design system (ui/theme/): card único de controles
com QGridLayout (mesmo padrão de Monitor/Traceroute), presets como grupo de
chips em vez de combobox, barra de progresso com destaque visual maior (é o
principal feedback de uma operação longa) e cores por token na tabela de
resultados. core/network.py e ScanWorker não foram tocados — só a camada
visual.
"""
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QSpinBox,
    QComboBox, QPushButton, QButtonGroup, QTableWidget, QTableWidgetItem,
    QProgressBar, QLabel, QHeaderView, QFileDialog, QCheckBox,
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import pyqtSignal, QTimer

from core.models import IPVersion
from core.workers import ScanWorker
from .widgets._utils import field_label as _lbl, TABLE_STYLE
from .widgets._worker_tab import WorkerTabMixin
from .theme.tokens import DARK, SPACING, RADIUS
from .theme.components import card_frame, primary_button, secondary_button
from .widgets._reflow_row import ReflowRow


_PRESETS: list[tuple[str, str]] = [
    ("Top 20", "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1723,3306,3389,5900,8080,8443"),
    ("Top 100", "7,9,13,21,22,23,25,26,37,53,79,80,81,88,106,110,111,113,119,135,139,143,"
                "144,179,199,389,427,443,444,445,465,513,514,515,543,544,548,554,587,631,"
                "646,873,990,993,995,1025,1026,1027,1028,1029,1110,1433,1720,1723,1755,"
                "1900,2000,2001,2049,2121,2717,3000,3128,3306,3389,3986,4899,5000,5009,"
                "5051,5060,5101,5190,5357,5432,5631,5666,5800,5900,6000,6001,6646,7070,"
                "8000,8008,8009,8080,8081,8443,8888,9100,9999,10000,32768,49152,49153,"
                "49154,49155,49156,49157"),
    ("Todas (1-65535)", "1-65535"),
]

_CHIP_QSS = (
    f"QPushButton{{background:palette(button);color:palette(button-text);"
    f"border-radius:{RADIUS.sm}px;font-size:11px;border:none;padding:5px {SPACING.sm}px;}}"
    f"QPushButton:hover{{background:palette(mid);}}"
    f"QPushButton:checked{{background:{DARK.primary};color:{DARK.on_primary};font-weight:bold;}}"
)


class ScanTab(WorkerTabMixin, QWidget):
    scan_finished = pyqtSignal(str, int)

    # Limite de linhas renderizadas na QTableWidget. Cada QTableWidgetItem
    # inserido custa ~1ms mesmo em lote (medido com 65535 linhas ≈ 70s) —
    # um scan "Todas (1-65535)" em UDP com "open|filtered" marcado pode
    # bater esse número de resultados. Além do limite, os resultados
    # continuam sendo coletados em _results e saem inteiros no "Exportar
    # CSV"; só a tabela ao vivo é que para de crescer. Ver docs/PERFORMANCE.md.
    _MAX_TABLE_ROWS = 5000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ScanWorker | None = None
        self._results: list[tuple] = []
        self._manually_stopped = False
        # Renderização incremental: com o preset "Todas (1-65535)" o scan
        # pode emitir dezenas de milhares de port_result/progress em
        # segundos — atualizar a tabela/progress bar a cada sinal trava a
        # UI thread. Resultados/progresso ficam em buffer e um QTimer (10Hz,
        # mesmo padrão de ui/widgets/rtt_graph.py) esvazia em lotes.
        self._pending_rows: list[tuple] = []
        self._pending_progress: tuple[int, int] | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(SPACING.lg, SPACING.lg, SPACING.lg, SPACING.lg)
        root.setSpacing(SPACING.md)

        # ── Card único de controles ──────────────────────────────────
        panel = card_frame(RADIUS.md)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(SPACING.lg, SPACING.md, SPACING.lg, SPACING.md)
        pl.setSpacing(SPACING.sm)

        grid = QGridLayout()
        grid.setHorizontalSpacing(SPACING.sm)
        grid.setVerticalSpacing(2)
        grid.setColumnStretch(0, 1)  # host — expansível

        grid.addWidget(_lbl("HOST / IP"), 0, 0)
        grid.addWidget(_lbl("PORTAS"), 0, 1)
        grid.addWidget(_lbl("TIMEOUT"), 0, 2)
        grid.addWidget(_lbl("THREADS"), 0, 3)
        grid.addWidget(_lbl("VERSÃO IP"), 0, 4)
        grid.addWidget(_lbl("PROTOCOLO"), 0, 5)

        self._inp_host = QLineEdit()
        self._inp_host.setPlaceholderText("Host ou IP")
        self._inp_host.setFixedHeight(34)
        self._inp_host.setMinimumWidth(140)

        self._inp_ports = QLineEdit()
        self._inp_ports.setPlaceholderText("1-1024,3389,8080")
        self._inp_ports.setFixedHeight(34)
        self._inp_ports.setMinimumWidth(140)
        self._inp_ports.textEdited.connect(self._on_ports_edited)

        self._inp_timeout = QSpinBox()
        self._inp_timeout.setRange(50, 10000)
        self._inp_timeout.setValue(200)
        self._inp_timeout.setSuffix(" ms")
        self._inp_timeout.setFixedHeight(34)
        self._inp_timeout.setFixedWidth(100)

        self._inp_threads = QSpinBox()
        self._inp_threads.setRange(1, 512)
        self._inp_threads.setValue(200)
        self._inp_threads.setFixedHeight(34)
        self._inp_threads.setFixedWidth(75)

        self._cmb_ip = QComboBox()
        for v in IPVersion:
            self._cmb_ip.addItem(v.value, v)
        self._cmb_ip.setFixedHeight(34)
        self._cmb_ip.setFixedWidth(75)

        self._cmb_proto = QComboBox()
        for label in ("TCP", "UDP", "TCP+UDP"):
            self._cmb_proto.addItem(label, label)
        self._cmb_proto.setFixedHeight(34)
        self._cmb_proto.setFixedWidth(95)

        grid.addWidget(self._inp_host,    1, 0)
        grid.addWidget(self._inp_ports,   1, 1)
        grid.addWidget(self._inp_timeout, 1, 2)
        grid.addWidget(self._inp_threads, 1, 3)
        grid.addWidget(self._cmb_ip,      1, 4)
        grid.addWidget(self._cmb_proto,   1, 5)
        pl.addLayout(grid)

        # ── Presets como grupo de chips + ação ───────────────────────
        # ReflowRow em vez de QHBoxLayout puro: em janelas estreitas (perto
        # do mínimo de 800x500) essa linha não cabia mais sem comprimir
        # texto de botão/chip a ponto de ficar ilegível — ver
        # docs/redesign/VERIFICACAO_FASE3.md. ReflowRow mantém a aparência
        # de linha única com stretch em janelas largas (nada muda em
        # ~1100px+) e só quebra pra duas linhas quando realmente não cabe.
        lbl_preset = _lbl("PREDEFINIÇÃO")
        self._chip_group = QButtonGroup(self)
        self._chip_group.setExclusive(True)
        chips = []
        for name, ports in _PRESETS:
            chip = QPushButton(name)
            chip.setCheckable(True)
            chip.setFixedHeight(26)
            chip.setStyleSheet(_CHIP_QSS)
            chip.clicked.connect(lambda _checked, p=ports: self._apply_preset(p))
            self._chip_group.addButton(chip)
            chips.append(chip)

        self._chk_udp_filtered = QCheckBox("UDP open|filtered")
        self._chk_udp_filtered.setStyleSheet("color:palette(placeholder-text); font-size:12px;")

        self._btn_start = primary_button("Iniciar Scan", icon="▶")
        self._btn_start.setFixedHeight(30)
        self._btn_start.clicked.connect(self._start)

        self._btn_stop = secondary_button("Parar", icon="⏹")
        self._btn_stop.setFixedHeight(30)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop)

        self._btn_export = secondary_button("Exportar CSV", icon="💾")
        self._btn_export.setFixedHeight(30)
        self._btn_export.setEnabled(False)
        self._btn_export.clicked.connect(self._export_csv)

        action_row = ReflowRow(
            left=[lbl_preset, *chips, SPACING.md, self._chk_udp_filtered],
            right=[self._btn_start, self._btn_stop, self._btn_export],
            spacing=SPACING.xs,
        )
        pl.addWidget(action_row)

        root.addWidget(panel)

        # ── Progresso — feedback principal de uma operação longa ────
        prog_card = card_frame(RADIUS.md)
        prog_layout = QHBoxLayout(prog_card)
        prog_layout.setContentsMargins(SPACING.lg, SPACING.sm, SPACING.lg, SPACING.sm)
        prog_layout.setSpacing(SPACING.md)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setFormat("%p%  —  %v / %m portas")
        self._progress.setFixedHeight(28)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background:palette(button); border-radius:{RADIUS.sm}px; color:palette(button-text);
                text-align:center; font-size:13px; font-weight:bold;
            }}
            QProgressBar::chunk {{ background:{DARK.primary}; border-radius:{RADIUS.sm}px; }}
        """)
        self._lbl_open = QLabel("Abertas: 0")
        self._lbl_open.setStyleSheet(f"color:{DARK.success}; font-size:14px; font-weight:bold; min-width:90px;")
        prog_layout.addWidget(self._progress, 1)
        prog_layout.addWidget(self._lbl_open)
        root.addWidget(prog_card)

        # ── Tabela ─────────────────────────────────────────────────────
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Porta", "Proto", "Serviço", "RTT", "Status"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 60)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet(
            TABLE_STYLE + "QTableWidget { alternate-background-color:palette(alternate-base); border:none; }"
        )
        root.addWidget(self._table, 1)

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(100)  # max 10 Hz, mesmo throttle do RttGraph
        self._flush_timer.timeout.connect(self._flush_pending)
        self._flush_timer.start()

    # ------------------------------------------------------------------

    def _apply_preset(self, ports: str):
        self._inp_ports.setText(ports)

    def _on_ports_edited(self):
        checked = self._chip_group.checkedButton()
        if checked is not None:
            # QButtonGroup exclusivo ignora setChecked(False) no único botão
            # marcado (mantém sempre 1 selecionado) — precisa soltar a
            # exclusividade momentaneamente para permitir "nenhum marcado".
            self._chip_group.setExclusive(False)
            checked.setChecked(False)
            self._chip_group.setExclusive(True)

    def _worker_signal_pairs(self):
        return [
            ("port_result", "_on_port_result"),
            ("progress",    "_on_progress"),
            ("finished_ok", "_on_finished"),
            ("error",       "_on_error"),
        ]

    def _start(self):
        host = self._inp_host.text().strip()
        if not host:
            return

        self._cleanup_worker()

        self._results.clear()
        self._table.setRowCount(0)
        self._open_count = 0
        self._manually_stopped = False
        self._lbl_open.setText("Abertas: 0")
        self._btn_export.setEnabled(False)
        self._pending_rows.clear()
        self._pending_progress = None

        port_spec = self._inp_ports.text().strip()
        ip_version = self._cmb_ip.currentData()
        timeout_ms = self._inp_timeout.value()
        threads = self._inp_threads.value()
        protocol = self._cmb_proto.currentData()

        self._worker = ScanWorker(host, port_spec, ip_version, timeout_ms, threads, protocol)
        self._worker.port_result.connect(self._on_port_result)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        from core.network import _parse_ports
        try:
            n_ports = len(_parse_ports(port_spec))
            multiplier = 2 if protocol == "TCP+UDP" else 1
            total = n_ports * multiplier
        except Exception:
            total = 1024
        self._progress.setRange(0, total)
        self._progress.setValue(0)
        self._progress.setFormat(f"%p%  —  %v / {total} portas")

        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._worker.start()

    def _stop(self):
        self._manually_stopped = True
        if self._worker and self._worker.isRunning():
            self._worker.stop()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_port_result(self, port: int, is_open: bool, ms: float, protocol: str):
        is_filtered = (
            not is_open
            and protocol == "UDP"
            and self._chk_udp_filtered.isChecked()
        )
        if not is_open and not is_filtered:
            return

        self._open_count = getattr(self, "_open_count", 0) + 1
        if self._open_count > self._MAX_TABLE_ROWS:
            suffix = f"  (exibindo {self._MAX_TABLE_ROWS} — CSV tem os {self._open_count})"
        else:
            suffix = ""
        self._lbl_open.setText(f"Abertas: {self._open_count}{suffix}")
        self._results.append((port, is_open, ms, protocol))
        # A linha só é inserida na tabela no próximo tick do _flush_timer —
        # ver comentário em __init__ sobre renderização incremental.
        self._pending_rows.append((port, is_open, ms, protocol))

    def _insert_row(self, port: int, is_open: bool, ms: float, protocol: str):
        try:
            import socket
            svc = socket.getservbyport(port, protocol.lower() if protocol in ("TCP", "UDP") else "tcp")
        except OSError:
            svc = "—"

        status_text  = "● Aberta"       if is_open else "◎ open|filtered"
        status_color = DARK.success     if is_open else DARK.warning
        proto_color  = DARK.link if protocol == "UDP" else DARK.info
        row = self._table.rowCount()
        self._table.insertRow(row)

        def cell(text: str, color: str | None) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            if color is not None:
                item.setForeground(QColor(color))
            return item

        self._table.setItem(row, 0, cell(str(port),      DARK.success))
        self._table.setItem(row, 1, cell(protocol,        proto_color))
        self._table.setItem(row, 2, cell(svc,              DARK.text_muted))
        self._table.setItem(row, 3, cell(f"{ms:.1f} ms",  None))  # cor padrão da tabela (palette(text))
        self._table.setItem(row, 4, cell(status_text,      status_color))

    def _on_progress(self, done: int, total: int):
        self._pending_progress = (done, total)

    def _flush_pending(self):
        """Esvazia em lote o que _on_progress/_on_port_result acumularam
        desde o último tick (10 Hz) — evita travar a UI thread com milhares
        de setValue()/insertRow() individuais durante um scan de "Todas"."""
        if self._pending_progress is not None:
            done, total = self._pending_progress
            self._progress.setValue(done)
            self._pending_progress = None

        if not self._pending_rows:
            return
        rows, self._pending_rows = self._pending_rows, []
        room = self._MAX_TABLE_ROWS - self._table.rowCount()
        if room <= 0:
            return
        self._table.setUpdatesEnabled(False)
        for port, is_open, ms, protocol in rows[:room]:
            self._insert_row(port, is_open, ms, protocol)
        self._table.setUpdatesEnabled(True)
        self._table.scrollToBottom()

    def _on_finished(self):
        self._flush_pending()
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_export.setEnabled(bool(self._results))
        if not self._manually_stopped:
            host = self._inp_host.text().strip()
            self.scan_finished.emit(host, getattr(self, "_open_count", 0))

    def _on_error(self, msg: str):
        self._on_finished()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "nocping_scan.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Porta", "Protocolo", "Serviço", "RTT (ms)", "Status"])
            for port, is_open, ms, protocol in self._results:
                try:
                    import socket
                    svc = socket.getservbyport(port, protocol.lower() if protocol in ("TCP", "UDP") else "tcp")
                except OSError:
                    svc = ""
                writer.writerow([port, protocol, svc, f"{ms:.1f}", "Aberta" if is_open else "Fechada"])
