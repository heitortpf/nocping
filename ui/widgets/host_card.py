"""
NOCPing — ui/widgets/host_card.py
Card individual por host — layout com seções separadas e hierarquia visual clara.

Redesenhado para usar o design system (ui/theme/): status_badge/cores
compartilhadas com o resto do app (STATUS_COLOR/STATUS_LABEL não são mais
duplicadas aqui), RTT atual em destaque tipográfico maior (TYPOGRAPHY.hero),
stats secundárias (média/jitter/perda) menores, e rodapé de ações compacto.
Jitter é novo aqui — mesmo cálculo (stdev dos últimos RTTs) já usado em
QuickPingTab. HostCard.status_changed, PingWorker e a gravação no
HistoryStore em _on_result não foram alterados.
"""
import csv
import statistics as _stats
from collections import deque

from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.models import ProbeConfig, ProbeMode, IPVersion, HostStatus, PingResult
from core.workers import PingWorker
from core.history_store import HistoryStore
from ._utils import rtt_color as _rtt_color
from ..theme.tokens import DARK, SPACING, RADIUS, TYPOGRAPHY
from ..theme.components import (
    STATUS_COLOR, STATUS_LABEL, primary_button, secondary_button,
)


def _stat_col(label: str, value_widget: QLabel) -> QVBoxLayout:
    """Coluna de estatística: rótulo pequeno em cima, valor embaixo."""
    col = QVBoxLayout()
    col.setSpacing(1)
    lbl = QLabel(label)
    lbl.setStyleSheet(f"color:{DARK.text_muted}; font-size:10px; letter-spacing:0.5px;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
    col.addWidget(lbl)
    col.addWidget(value_widget)
    return col


class HostCard(QFrame):
    removed        = pyqtSignal(object)
    status_changed = pyqtSignal(str, object, object)  # host, old, new

    def __init__(self, config: ProbeConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._worker: PingWorker | None = None
        self._status = HostStatus.IDLE
        self._results: deque[PingResult] = deque(maxlen=5000)

        # Contadores incrementais O(1) para estatísticas
        self._ok_count = 0
        self._total_count = 0
        self._sum_ms = 0.0
        self._min_ms = float("inf")
        self._max_ms = 0.0
        self._recent_rtts: deque[float] = deque(maxlen=50)  # p/ jitter (stdev)

        self.setFixedWidth(320)
        self.setObjectName("HostCard")
        self.setStyleSheet(f"""
            #HostCard {{
                background: palette(base);
                border: 1px solid palette(mid);
                border-radius: {RADIUS.md}px;
            }}
        """)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Cabeçalho: dot + host + status_badge + remover ──────────────
        header = QFrame()
        header.setObjectName("CardHeader")
        header.setStyleSheet(f"""
            #CardHeader {{
                background: palette(alternate-base);
                border-top-left-radius: {RADIUS.md}px;
                border-top-right-radius: {RADIUS.md}px;
                border-bottom: 1px solid palette(mid);
            }}
        """)
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        h_layout.setSpacing(4)

        title_row = QHBoxLayout()
        self._indicator = QLabel("●")
        self._indicator.setStyleSheet(f"color:{STATUS_COLOR[HostStatus.IDLE]}; font-size:16px;")
        self._indicator.setFixedWidth(20)

        self._lbl_host = QLabel(self.config.host)
        self._lbl_host.setToolTip(self.config.host)
        font_host = QFont()
        font_host.setPointSize(13)
        font_host.setBold(True)
        self._lbl_host.setFont(font_host)
        self._lbl_host.setStyleSheet("color:palette(text);")

        # status_badge — mesma cor/texto por HostStatus usados em todo o app
        # (ui/theme/components.py); atualizado in-place em _set_status().
        self._lbl_status_text = QLabel(STATUS_LABEL[HostStatus.IDLE])
        self._lbl_status_text.setStyleSheet(
            f"color:{STATUS_COLOR[HostStatus.IDLE]}; font-size:10px; font-weight:bold;"
        )

        btn_remove = QPushButton("✕")
        btn_remove.setFixedSize(22, 22)
        btn_remove.setStyleSheet(
            f"QPushButton{{background:transparent;color:{DARK.text_muted};border:none;font-size:14px;}}"
            f"QPushButton:hover{{color:{DARK.danger};}}"
        )
        btn_remove.clicked.connect(lambda: self.removed.emit(self))

        title_row.addWidget(self._indicator)
        title_row.addWidget(self._lbl_host, 1)
        title_row.addWidget(self._lbl_status_text)
        title_row.addSpacing(6)
        title_row.addWidget(btn_remove)
        h_layout.addLayout(title_row)

        # Modo + Porta + IP resolvido
        sub_row = QHBoxLayout()
        _mode_str = self.config.mode.value
        if self.config.mode != ProbeMode.ICMP:
            _mode_str += f"  ·  porta {self.config.port}"
        self._lbl_mode = QLabel(_mode_str)
        self._lbl_mode.setStyleSheet(f"color:{DARK.text_muted}; font-size:11px;")
        self._lbl_ip = QLabel("resolvendo…")
        self._lbl_ip.setStyleSheet(f"color:{DARK.text_muted}; font-size:11px;")
        self._lbl_ip.setAlignment(Qt.AlignmentFlag.AlignRight)
        sub_row.addWidget(self._lbl_mode)
        sub_row.addStretch()
        sub_row.addWidget(self._lbl_ip)
        h_layout.addLayout(sub_row)

        root.addWidget(header)

        # ── Corpo ────────────────────────────────────────────────────────
        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(SPACING.md, SPACING.sm, SPACING.md, SPACING.sm)
        body_layout.setSpacing(SPACING.sm)

        # Seletor IPv4 / IPv6
        ip_row = QHBoxLayout()
        ip_lbl = QLabel("VERSÃO IP:")
        ip_lbl.setStyleSheet(f"color:{DARK.text_muted}; font-size:10px; letter-spacing:0.5px;")
        ip_row.addWidget(ip_lbl)
        ip_row.addSpacing(6)

        self._ip_group = QButtonGroup(self)
        self._ip_group.setExclusive(True)
        for label, version in [("Auto", IPVersion.AUTO),
                                ("IPv4", IPVersion.IPV4),
                                ("IPv6", IPVersion.IPV6)]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            btn.setFixedWidth(44)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:palette(button); color:palette(button-text);
                    border-radius:4px; font-size:11px; border:none;
                }}
                QPushButton:checked {{ background:{DARK.primary}; color:{DARK.on_primary}; font-weight:bold; }}
                QPushButton:hover:!checked {{ background:palette(mid); color:palette(text); }}
            """)
            btn.setProperty("version", version)
            btn.clicked.connect(self._on_ip_version_changed)
            self._ip_group.addButton(btn)
            ip_row.addWidget(btn)
            if version == self.config.ip_version:
                btn.setChecked(True)
        ip_row.addStretch()
        body_layout.addLayout(ip_row)

        body_layout.addWidget(_hline())

        # ── RTT atual — hero, tipograficamente maior que o resto ────────
        self._val_rtt = QLabel("—")
        self._val_rtt.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._val_rtt.setStyleSheet(
            f"color:{DARK.text_muted}; font-size:{TYPOGRAPHY.hero.size}px; "
            f"font-weight:{TYPOGRAPHY.hero.weight};"
        )
        body_layout.addWidget(self._val_rtt)

        # ── Stats secundárias — Média / Jitter / Perda (menores que o hero) ─
        self._val_avg    = _stat_value()
        self._val_jitter = _stat_value()
        self._val_loss   = _stat_value("0%")

        stats_row = QHBoxLayout()
        stats_row.setSpacing(0)
        stats_row.addLayout(_stat_col("MÉDIA",  self._val_avg))
        stats_row.addWidget(_vline())
        stats_row.addLayout(_stat_col("JITTER", self._val_jitter))
        stats_row.addWidget(_vline())
        stats_row.addLayout(_stat_col("PERDA",  self._val_loss))
        body_layout.addLayout(stats_row)

        # Min / Max / Seq — terciário, discreto
        secondary = QHBoxLayout()
        self._lbl_min  = _dim_label("Mín: —")
        self._lbl_max  = _dim_label("Máx: —")
        self._lbl_seq  = _dim_label("Seq: 0")
        for l in (self._lbl_min, self._lbl_max, self._lbl_seq):
            secondary.addWidget(l)
            if l is not self._lbl_seq:
                secondary.addStretch()
        body_layout.addLayout(secondary)

        body_layout.addWidget(_hline())

        # Mini-gráfico RTT — _FlowLayout do MonitorTab depende do tamanho
        # deste card para quebrar linha; NÃO alterar setFixedHeight sem
        # revalidar o redimensionamento da janela manualmente.
        from .rtt_graph import RttGraph
        self._graph = RttGraph()
        self._graph.setFixedHeight(80)
        body_layout.addWidget(self._graph)

        body_layout.addWidget(_hline())

        # ── Rodapé compacto: Histórico/Exportar + Iniciar/Parar ──────────
        _link_style = (
            f"QPushButton{{color:{DARK.primary};font-size:10px;border:none;background:transparent;}}"
            f"QPushButton:hover{{color:{DARK.primary_hover};text-decoration:underline;}}"
        )
        footer_row = QHBoxLayout()
        btn_history = QPushButton("⏱ Histórico")
        btn_history.setFlat(True)
        btn_history.setStyleSheet(_link_style)
        btn_history.clicked.connect(self._open_history)
        footer_row.addWidget(btn_history, alignment=Qt.AlignmentFlag.AlignLeft)

        btn_export_rtt = QPushButton("⬇ Exportar RTT")
        btn_export_rtt.setFlat(True)
        btn_export_rtt.setStyleSheet(_link_style)
        btn_export_rtt.clicked.connect(self._export_rtt)
        footer_row.addWidget(btn_export_rtt, alignment=Qt.AlignmentFlag.AlignRight)
        body_layout.addLayout(footer_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(SPACING.sm)
        self._btn_start = primary_button("Iniciar", icon="▶")
        self._btn_stop  = secondary_button("Parar", icon="⏹")
        self._btn_start.setFixedHeight(30)
        self._btn_stop.setFixedHeight(30)
        self._btn_stop.setEnabled(False)
        self._btn_start.clicked.connect(self.start)
        self._btn_stop.clicked.connect(self.stop)
        btn_row.addWidget(self._btn_start, 1)
        btn_row.addWidget(self._btn_stop, 1)
        body_layout.addLayout(btn_row)

        root.addWidget(body)

    # ------------------------------------------------------------------
    # Controle
    # ------------------------------------------------------------------

    def start(self):
        if self._worker and self._worker.isRunning():
            return
        self._results.clear()
        self._ok_count = 0
        self._total_count = 0
        self._sum_ms = 0.0
        self._min_ms = float("inf")
        self._max_ms = 0.0
        self._recent_rtts.clear()
        self._graph.reset()
        self._reset_stats()
        self._set_status(HostStatus.RUNNING)
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._lbl_ip.setText("resolvendo…")

        self._worker = PingWorker(self.config)
        self._worker.result.connect(self._on_result)
        self._worker.resolved.connect(self._on_resolved)
        self._worker.error.connect(self._on_error)
        self._worker.stats.connect(self._on_finished)
        self._worker.start()

    def stop(self):
        if self._worker:
            self._worker.stop()
        self._reset_buttons_idle()
        if self._status == HostStatus.RUNNING:
            self._set_status(HostStatus.IDLE)

    def start_if_idle(self):
        if self._status == HostStatus.IDLE:
            self.start()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_resolved(self, ip: str, version: str):
        self._lbl_ip.setText(f"{ip}  [{version}]")

    def _on_result(self, r: PingResult):
        self._results.append(r)
        HistoryStore.instance().record(self.config.host, r)
        timeout = not r.success or r.elapsed_ms <= 0
        self._graph.add_point(r.elapsed_ms if not timeout else 0.0, timeout)

        # Contadores incrementais O(1)
        self._total_count += 1
        if r.success and r.elapsed_ms > 0:
            self._ok_count += 1
            self._sum_ms += r.elapsed_ms
            self._recent_rtts.append(r.elapsed_ms)
            if r.elapsed_ms < self._min_ms:
                self._min_ms = r.elapsed_ms
            if r.elapsed_ms > self._max_ms:
                self._max_ms = r.elapsed_ms

        if r.success:
            self._set_status(HostStatus.UP)
            c = _rtt_color(r.elapsed_ms)
            self._val_rtt.setText(f"{r.elapsed_ms:.1f} ms")
            self._val_rtt.setStyleSheet(
                f"color:{c}; font-size:{TYPOGRAPHY.hero.size}px; font-weight:{TYPOGRAPHY.hero.weight};"
            )
        else:
            self._set_status(HostStatus.DOWN)
            self._val_rtt.setText("timeout")
            self._val_rtt.setStyleSheet(
                f"color:{DARK.danger}; font-size:18px; font-weight:{TYPOGRAPHY.hero.weight};"
            )

        # Estatísticas a partir dos contadores O(1)
        lost = self._total_count - self._ok_count
        loss_pct = lost / self._total_count * 100
        avg = self._sum_ms / self._ok_count if self._ok_count else 0.0
        mn = self._min_ms if self._ok_count else 0.0
        mx = self._max_ms if self._ok_count else 0.0

        # Jitter (stdev dos últimos RTTs) — mesmo cálculo do QuickPingTab
        if len(self._recent_rtts) > 1:
            jitter = _stats.stdev(self._recent_rtts)
        else:
            jitter = 0.0

        avg_c = _rtt_color(avg) if self._ok_count else DARK.text_muted
        self._val_avg.setText(f"{avg:.1f} ms" if self._ok_count else "—")
        self._val_avg.setStyleSheet(f"color:{avg_c}; font-size:{TYPOGRAPHY.value.size}px; font-weight:bold;")

        jit_c = _rtt_color(jitter * 2) if self._ok_count else DARK.text_muted
        self._val_jitter.setText(f"{jitter:.1f} ms" if self._ok_count else "—")
        self._val_jitter.setStyleSheet(f"color:{jit_c}; font-size:{TYPOGRAPHY.value.size}px; font-weight:bold;")

        loss_c = DARK.danger if loss_pct > 5 else (DARK.warning if loss_pct > 0 else DARK.success)
        self._val_loss.setText(f"{loss_pct:.0f}%")
        self._val_loss.setStyleSheet(f"color:{loss_c}; font-size:{TYPOGRAPHY.value.size}px; font-weight:bold;")

        self._lbl_min.setText(f"Mín: {mn:.1f}ms" if self._ok_count else "Mín: —")
        self._lbl_max.setText(f"Máx: {mx:.1f}ms" if self._ok_count else "Máx: —")
        self._lbl_seq.setText(f"Seq: {r.seq}")

    def _on_error(self, msg: str):
        self._set_status(HostStatus.ERROR)
        self._lbl_ip.setText(f"⚠  {msg[:36]}")
        self._val_rtt.setText("—")
        self._reset_buttons_idle()

    def _on_finished(self, _stats: dict):
        self._reset_buttons_idle()

    def _reset_buttons_idle(self):
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)

    def _on_ip_version_changed(self):
        for btn in self._ip_group.buttons():
            if btn.isChecked():
                self.config.ip_version = btn.property("version")
                if self._worker and self._worker.isRunning():
                    self._worker.stop()
                    self._worker.wait(400)
                    self.start()
                break

    def _open_history(self):
        from ui.widgets.history_dialog import HistoryDialog
        dlg = HistoryDialog(self.config.host, self)
        dlg.exec()

    def _export_rtt(self):
        if not self._results:
            return
        safe_host = self.config.host.replace(":", "_").replace("/", "_")
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar histórico RTT",
            f"rtt_{safe_host}.csv", "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Seq", "Sucesso", "RTT (ms)", "Nota"])
            for r in self._results:
                writer.writerow([r.seq, r.success, f"{r.elapsed_ms:.3f}", r.note])

    def _set_status(self, status: HostStatus):
        old = self._status
        self._status = status
        c = STATUS_COLOR[status]
        self._indicator.setStyleSheet(f"color:{c}; font-size:16px;")
        self._lbl_status_text.setText(STATUS_LABEL[status])
        self._lbl_status_text.setStyleSheet(
            f"color:{c}; font-size:10px; font-weight:bold;"
        )
        if old != status and status in (HostStatus.UP, HostStatus.DOWN, HostStatus.ERROR):
            self.status_changed.emit(self.config.host, old, status)

    def _reset_stats(self):
        self._val_rtt.setText("—")
        self._val_rtt.setStyleSheet(
            f"color:{DARK.text_muted}; font-size:{TYPOGRAPHY.hero.size}px; font-weight:{TYPOGRAPHY.hero.weight};"
        )
        for w in (self._val_avg, self._val_jitter, self._val_loss):
            w.setText("—")
            w.setStyleSheet(f"color:{DARK.text_muted}; font-size:{TYPOGRAPHY.value.size}px; font-weight:bold;")
        self._val_loss.setText("0%")
        self._lbl_min.setText("Mín: —")
        self._lbl_max.setText("Máx: —")
        self._lbl_seq.setText("Seq: 0")

    @property
    def status(self) -> HostStatus:
        return self._status


# ---------------------------------------------------------------------------
# Helpers de widgets
# ---------------------------------------------------------------------------

def _stat_value(text: str = "—") -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{DARK.text_muted}; font-size:{TYPOGRAPHY.value.size}px; font-weight:bold;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _dim_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{DARK.text_muted}; font-size:10px;")
    return lbl


def _hline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:palette(mid); margin:0;")
    f.setFixedHeight(1)
    return f


def _vline() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet("color:palette(mid);")
    f.setFixedWidth(1)
    f.setContentsMargins(0, 4, 0, 4)
    return f
