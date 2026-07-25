"""
NOCPing — ui/widgets/quick_ping_stats_panel.py
Painel de estatísticas do Quick Ping — faixa de status compacta (status,
IP resolvido, seq, duração) + uma linha de "stat cards" em destaque para
RTT atual, média, jitter, mínimo, máximo e perda.

Extraído de ui/quick_ping_tab.py. Este widget só renderiza — todo o cálculo
de estatísticas (contadores O(1), jitter via stdev, etc.) continua no
orquestrador (QuickPingTab), que chama os setters aqui com texto/cor prontos.
A API pública não mudou nesta redesign, só a estrutura interna.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from ..theme.tokens import DARK, SPACING
from ..theme.components import stat_card

_META_STYLE = f"color:{DARK.text_muted}; font-size:11px;"


class QuickPingStatsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(SPACING.sm)

        # ── Faixa de status/meta (compacta) ───────────────────────────
        info_row = QHBoxLayout()
        info_row.setSpacing(SPACING.sm)

        self._lbl_status_dot = QLabel("●")
        self._lbl_status_dot.setStyleSheet(f"color:{DARK.text_muted}; font-size:14px;")
        self._lbl_status = QLabel("INATIVO")
        self._lbl_status.setStyleSheet(f"color:{DARK.text_muted}; font-size:12px; font-weight:bold;")
        info_row.addWidget(self._lbl_status_dot)
        info_row.addWidget(self._lbl_status)

        self._lbl_resolved = QLabel("—")
        self._lbl_resolved.setStyleSheet(_META_STYLE)
        info_row.addWidget(self._lbl_resolved, 1)

        self._lbl_seq = QLabel("SEQ 0")
        self._lbl_seq.setStyleSheet(_META_STYLE)
        info_row.addWidget(self._lbl_seq)

        self._lbl_elapsed = QLabel("")
        self._lbl_elapsed.setStyleSheet(_META_STYLE)
        info_row.addWidget(self._lbl_elapsed)

        outer.addLayout(info_row)

        # ── Linha de stat cards em destaque ───────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(SPACING.sm)

        self._card_rtt,    self._val_rtt    = stat_card("RTT ATUAL")
        self._card_avg,    self._val_avg    = stat_card("MÉDIA")
        self._card_jitter, self._val_jitter = stat_card("JITTER")
        self._card_min,    self._val_min    = stat_card("MÍNIMO")
        self._card_max,    self._val_max    = stat_card("MÁXIMO")
        self._card_loss,   self._val_loss   = stat_card("PERDA %", "0%")

        for card in (self._card_rtt, self._card_avg, self._card_jitter,
                     self._card_min, self._card_max, self._card_loss):
            cards_row.addWidget(card, 1)

        outer.addLayout(cards_row)

    # ------------------------------------------------------------------
    # API pública (usada pelo orquestrador QuickPingTab)
    # ------------------------------------------------------------------

    def set_status(self, text: str, color: str):
        self._lbl_status_dot.setStyleSheet(f"color:{color}; font-size:14px;")
        self._lbl_status.setText(text)
        self._lbl_status.setStyleSheet(f"color:{color}; font-size:12px; font-weight:bold;")

    def set_resolved(self, text: str):
        self._lbl_resolved.setText(text)

    def set_rtt(self, text: str, color: str, font_size: int = 18):
        self._val_rtt.setText(text)
        self._val_rtt.setStyleSheet(f"color:{color}; font-size:{font_size}px; font-weight:bold;")

    def set_avg(self, text: str, color: str):
        self._val_avg.setText(text)
        self._val_avg.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

    def set_min(self, text: str, color: str):
        self._val_min.setText(text)
        self._val_min.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

    def set_max(self, text: str, color: str):
        self._val_max.setText(text)
        self._val_max.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

    def set_loss(self, text: str, color: str):
        self._val_loss.setText(text)
        self._val_loss.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

    def set_jitter(self, text: str, color: str):
        self._val_jitter.setText(text)
        self._val_jitter.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")

    def set_seq(self, text: str):
        self._lbl_seq.setText(f"SEQ {text}")

    def set_elapsed(self, text: str):
        self._lbl_elapsed.setText(text)

    def reset_display(self):
        for val_lbl in (self._val_rtt, self._val_avg, self._val_min,
                         self._val_max, self._val_jitter):
            val_lbl.setText("—")
            val_lbl.setStyleSheet(f"color:{DARK.text_muted}; font-size:18px; font-weight:bold;")
        self._val_loss.setText("0%")
        self._val_loss.setStyleSheet(f"color:{DARK.success}; font-size:18px; font-weight:bold;")
        self._lbl_seq.setText("SEQ 0")
        self._lbl_elapsed.setText("")
        self._lbl_resolved.setText("—")
