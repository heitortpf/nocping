"""
NOCPing — ui/main_window.py
Janela principal com abas, menu e barra de status.
"""
import base64

from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QApplication, QFileDialog,
    QSystemTrayIcon,
)
from PyQt6.QtCore import QSettings, QByteArray, QBuffer, QIODevice
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QAction, QPalette, QColor, QPainter, QPixmap, QPolygonF

from .monitor_tab import MonitorTab
from .quick_ping_tab import QuickPingTab
from .theme.tokens import DARK, LIGHT, ColorTokens
from .theme.components import count_badge
from .widgets.tray import SystemTray
from .widgets.sidebar import NavSidebar
from core.network import is_admin


def _palette_dict(t: ColorTokens) -> dict:
    return {
        QPalette.ColorRole.Window:          t.bg,
        QPalette.ColorRole.WindowText:      t.text_primary,
        QPalette.ColorRole.Base:            t.surface,
        QPalette.ColorRole.AlternateBase:   t.surface_elevated,
        QPalette.ColorRole.Text:            t.text_primary,
        QPalette.ColorRole.Button:          t.button_bg,
        QPalette.ColorRole.ButtonText:      t.text_primary,
        QPalette.ColorRole.Mid:             t.border,
        QPalette.ColorRole.Highlight:       t.primary,
        QPalette.ColorRole.HighlightedText: t.on_primary,
        QPalette.ColorRole.ToolTipBase:     t.tooltip_bg,
        QPalette.ColorRole.ToolTipText:     t.tooltip_fg,
        QPalette.ColorRole.PlaceholderText: t.text_secondary,
        QPalette.ColorRole.Link:            t.link,
    }


DARK_PALETTE = _palette_dict(DARK)
LIGHT_PALETTE = _palette_dict(LIGHT)

_arrow_cache: dict[str, str] = {}


def _arrow_url(direction: str, dark: bool) -> str:
    key = f"{direction}_{'dark' if dark else 'light'}"
    if key in _arrow_cache:
        return _arrow_cache[key]

    color = QColor((DARK if dark else LIGHT).text_primary)
    pts_up   = [QPointF(5, 2), QPointF(10, 9), QPointF(0, 9)]
    pts_down = [QPointF(0, 1), QPointF(10, 1), QPointF(5, 8)]
    pts = pts_up if direction == "up" else pts_down

    px = QPixmap(10, 10)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(color)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPolygon(QPolygonF(pts))
    p.end()

    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    px.save(buf, "PNG")
    b64 = base64.b64encode(ba.data()).decode()
    url = f"data:image/png;base64,{b64}"
    _arrow_cache[key] = url
    return url


def _build_stylesheet(dark: bool) -> str:
    up   = _arrow_url("up",   dark)
    down = _arrow_url("down", dark)
    t = DARK if dark else LIGHT

    return f"""
    QToolTip {{ color:{t.tooltip_fg}; background:{t.tooltip_bg}; border:1px solid {t.border}; }}
    QLineEdit, QComboBox {{
        background:{t.field_bg}; color:{t.text_primary}; border:1px solid {t.border};
        border-radius:4px; padding:3px 6px;
        selection-background-color:{t.primary}; selection-color:{t.on_primary};
    }}
    QLineEdit:focus, QComboBox:focus {{ border:1px solid {t.primary}; }}
    QSpinBox {{
        background:{t.field_bg}; color:{t.text_primary}; border:1px solid {t.border};
        border-radius:4px; padding:3px 6px;
        selection-background-color:{t.primary}; selection-color:{t.on_primary};
    }}
    QSpinBox:focus {{ border:1px solid {t.primary}; }}
    QSpinBox::up-button {{
        subcontrol-origin: border; subcontrol-position: top right;
        width:18px; background:{t.control_bg};
        border-left:1px solid {t.border}; border-top-right-radius:4px;
    }}
    QSpinBox::up-button:hover   {{ background:{t.control_hover}; }}
    QSpinBox::up-button:pressed {{ background:{t.control_press}; }}
    QSpinBox::down-button {{
        subcontrol-origin: border; subcontrol-position: bottom right;
        width:18px; background:{t.control_bg};
        border-left:1px solid {t.border}; border-bottom-right-radius:4px;
    }}
    QSpinBox::down-button:hover   {{ background:{t.control_hover}; }}
    QSpinBox::down-button:pressed {{ background:{t.control_press}; }}
    QSpinBox::up-arrow   {{ image: url({up});   width:8px; height:8px; }}
    QSpinBox::down-arrow {{ image: url({down}); width:8px; height:8px; }}
    QScrollBar:vertical {{ background:{t.surface_elevated}; width:8px; border-radius:4px; }}
    QScrollBar::handle:vertical {{ background:{t.border}; border-radius:4px; min-height:20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar:horizontal {{ background:{t.surface_elevated}; height:8px; border-radius:4px; }}
    QScrollBar::handle:horizontal {{ background:{t.border}; border-radius:4px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
    QSplitter::handle {{ background:{t.button_bg}; }}
"""

DARK_MENUBAR_STYLE = (
    f"QMenuBar{{background:{DARK.bg};color:{DARK.text_primary};}}"
    f"QMenuBar::item:selected{{background:{DARK.button_bg};}}"
    f"QMenu{{background:{DARK.surface_elevated};color:{DARK.text_primary};border:1px solid {DARK.button_bg};}}"
    f"QMenu::item:selected{{background:{DARK.button_bg};}}"
)

LIGHT_MENUBAR_STYLE = (
    f"QMenuBar{{background:{LIGHT.bg};color:{LIGHT.text_primary};}}"
    f"QMenuBar::item:selected{{background:{LIGHT.button_bg};}}"
    f"QMenu{{background:{LIGHT.surface};color:{LIGHT.text_primary};border:1px solid {LIGHT.border};}}"
    f"QMenu::item:selected{{background:{LIGHT.surface_elevated};}}"
)

DARK_STATUSBAR_STYLE  = f"QStatusBar{{background:{DARK.bg};color:{DARK.text_muted};font-size:11px;}}"
LIGHT_STATUSBAR_STYLE = f"QStatusBar{{background:{LIGHT.bg};color:{LIGHT.text_muted};font-size:11px;}}"


def detect_system_dark() -> bool:
    try:
        import darkdetect
        result = darkdetect.isDark()
        if result is not None:
            return bool(result)
    except ImportError:
        pass
    # Fallback: ask Qt about the current palette
    app = QApplication.instance()
    if app:
        return app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    return True


def apply_theme(app, dark: bool) -> None:
    palette = QPalette()
    for role, hex_color in (DARK_PALETTE if dark else LIGHT_PALETTE).items():
        palette.setColor(role, QColor(hex_color))
    app.setPalette(palette)
    app.setStyleSheet(_build_stylesheet(dark))


class MainWindow(QMainWindow):
    _instances: list["MainWindow"] = []

    # Única fonte de verdade pra ordem/índice das seções — usado por
    # show_section() e por quem mais precisar de navegação programática
    # (ex.: take_shots.py). Se a navegação mudar de novo no futuro, só isto
    # (e o _on_tab_activated correspondente) precisa mudar.
    SECTIONS: tuple[str, ...] = (
        "quick_ping", "monitor", "port_scan", "banner_tls", "traceroute", "mtr",
    )

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOCPing")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._is_dark = (
            MainWindow._instances[0]._is_dark
            if MainWindow._instances
            else detect_system_dark()
        )
        MainWindow._instances.append(self)

        self._settings = QSettings("NOCPing", "NOCPing")
        self._notif_enabled: bool = self._settings.value(
            "notifications_enabled", True, type=bool
        )

        self._build_menu()
        self._build_tabs()
        self._build_status_bar()
        self._build_tray()
        self._apply_window_theme()
        QApplication.instance().aboutToQuit.connect(self._shutdown)

    def _build_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("Arquivo")
        act_new = QAction("Nova Janela", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._open_new_window)
        file_menu.addAction(act_new)
        file_menu.addSeparator()
        act_shot = QAction("Salvar Screenshot...", self)
        act_shot.setShortcut("Ctrl+P")
        act_shot.triggered.connect(self._save_screenshot)
        file_menu.addAction(act_shot)
        file_menu.addSeparator()
        act_quit = QAction("Sair", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(QApplication.quit)
        file_menu.addAction(act_quit)

        view_menu = menu.addMenu("Visualizar")
        self._act_notif = QAction("Notificações de host", self)
        self._act_notif.setCheckable(True)
        self._act_notif.setChecked(self._notif_enabled)
        self._act_notif.triggered.connect(self._toggle_notifications)
        view_menu.addAction(self._act_notif)

        help_menu = menu.addMenu("Ajuda")
        act_about = QAction("Sobre NOCPing", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

        self._btn_theme = QPushButton()
        self._btn_theme.setFlat(True)
        self._btn_theme.setFixedHeight(24)
        self._btn_theme.setToolTip("Alternar tema claro/escuro")
        self._btn_theme.clicked.connect(self._toggle_theme)
        menu.setCornerWidget(self._btn_theme)

    def _build_tabs(self):
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self._sidebar = NavSidebar()
        self._sidebar.page_changed.connect(self._on_tab_activated)
        central_layout.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        central_layout.addWidget(self._stack, 1)

        self._quick_ping = QuickPingTab()
        self._quick_ping.ping_finished.connect(self._on_quick_ping_finished)
        self._quick_ping.host_status_changed.connect(self._on_host_status_changed)
        self._monitor = MonitorTab()
        self._monitor.status_changed.connect(self._update_status_bar)
        self._monitor.host_status_changed.connect(self._on_host_status_changed)
        self._scan:       "ScanTab | None"       = None
        self._banner:     "BannerTab | None"     = None
        self._traceroute: "TracerouteTab | None" = None
        self._mtr:        "MTRTab | None"        = None
        self._initialized_tabs: set[int] = {0, 1}

        self._stack.addWidget(self._quick_ping)  # index 0
        self._stack.addWidget(self._monitor)     # index 1
        self._stack.addWidget(QWidget())         # index 2 — Port Scan (lazy)
        self._stack.addWidget(QWidget())         # index 3 — Banner/TLS (lazy)
        self._stack.addWidget(QWidget())         # index 4 — Traceroute (lazy)
        self._stack.addWidget(QWidget())         # index 5 — MTR (lazy)

        self.setCentralWidget(central)
        self._sidebar.set_current(0)
        self._stack.setCurrentIndex(0)

    def _on_tab_activated(self, index: int):
        if index not in self._initialized_tabs:
            self._initialized_tabs.add(index)

            widget = None
            if index == 2:
                from .scan_tab import ScanTab
                self._scan = ScanTab()
                self._scan.scan_finished.connect(self._on_scan_finished)
                widget = self._scan
            elif index == 3:
                from .banner_tab import BannerTab
                self._banner = BannerTab()
                self._banner.banner_finished.connect(self._on_banner_finished)
                widget = self._banner
            elif index == 4:
                from .traceroute_tab import TracerouteTab
                self._traceroute = TracerouteTab()
                self._traceroute.traceroute_finished.connect(self._on_traceroute_finished)
                widget = self._traceroute
            elif index == 5:
                from .mtr_tab import MTRTab
                self._mtr = MTRTab()
                self._mtr.mtr_finished.connect(self._on_mtr_finished)
                widget = self._mtr

            if widget is not None:
                old = self._stack.widget(index)
                self._stack.insertWidget(index, widget)
                self._stack.removeWidget(old)
                old.deleteLater()

        self._stack.setCurrentIndex(index)

    def show_section(self, name: str):
        """Navega programaticamente para uma seção pelo nome (mesmo efeito de
        clicar o item correspondente na sidebar, lazy-load incluso) — sem
        depender de coordenadas de tela ou de conhecer a estrutura interna
        de widgets. Único ponto de navegação automatizada (usado por
        take_shots.py); se a navegação mudar de novo, só isto precisa mudar.
        """
        index = self.SECTIONS.index(name)
        self._sidebar.set_current(index)
        self._on_tab_activated(index)

    def _build_status_bar(self):
        self._status_bar = self.statusBar()

        self._lbl_hosts = QLabel("Hosts: 0")
        self._lbl_up    = count_badge("▲ Up: 0", DARK.success)
        self._lbl_down  = count_badge("▼ Down: 0", DARK.danger)
        self._lbl_admin = QLabel()

        _admin = is_admin()
        admin_txt   = "🔐 Admin" if _admin else "⚠ Sem Admin (ICMP/UDP indisponível)"
        admin_color = DARK.success if _admin else DARK.warning
        self._lbl_admin.setText(admin_txt)
        self._lbl_admin.setStyleSheet(f"color:{admin_color};")

        for lbl in (self._lbl_hosts, self._lbl_up, self._lbl_down, self._lbl_admin):
            self._status_bar.addPermanentWidget(lbl)

    def _apply_window_theme(self):
        dark = self._is_dark
        self.menuBar().setStyleSheet(DARK_MENUBAR_STYLE if dark else LIGHT_MENUBAR_STYLE)
        self._status_bar.setStyleSheet(DARK_STATUSBAR_STYLE if dark else LIGHT_STATUSBAR_STYLE)
        if dark:
            self._btn_theme.setText("🌙  Escuro")
            self._btn_theme.setToolTip("Alternar para tema claro")
        else:
            self._btn_theme.setText("☀  Claro")
            self._btn_theme.setToolTip("Alternar para tema escuro")
        self._btn_theme.adjustSize()

    def _build_tray(self):
        self._tray = SystemTray(self.windowIcon(), self)

    def _toggle_notifications(self, checked: bool):
        self._notif_enabled = checked
        self._settings.setValue("notifications_enabled", checked)

    def _on_host_status_changed(self, host: str, old, new):
        from core.models import HostStatus
        if not self._notif_enabled:
            return
        if new == HostStatus.DOWN:
            self._tray.showMessage(
                "Host offline", f"{host} está OFFLINE",
                QSystemTrayIcon.MessageIcon.Critical, 4000,
            )
        elif new == HostStatus.UP and old == HostStatus.DOWN:
            self._tray.showMessage(
                "Host online", f"{host} voltou ONLINE",
                QSystemTrayIcon.MessageIcon.Information, 3000,
            )
        elif new == HostStatus.ERROR:
            self._tray.showMessage(
                "Erro no Host", f"Erro monitorando {host}",
                QSystemTrayIcon.MessageIcon.Warning, 4000,
            )

    def _on_quick_ping_finished(self, host: str, success: bool, msg: str):
        if not self._notif_enabled: return
        icon = QSystemTrayIcon.MessageIcon.Information if success else QSystemTrayIcon.MessageIcon.Warning
        title = f"Ping Concluído: {host}" if success else f"Ping Falhou: {host}"
        self._tray.showMessage(title, msg, icon, 4000)

    def _on_scan_finished(self, host: str, open_ports: int):
        if not self._notif_enabled: return
        icon = QSystemTrayIcon.MessageIcon.Information
        title = f"Scan Concluído: {host}"
        msg = f"{open_ports} portas abertas encontradas." if open_ports > 0 else "Nenhuma porta aberta encontrada."
        self._tray.showMessage(title, msg, icon, 4000)

    def _on_banner_finished(self, host: str, port: int, success: bool):
        if not self._notif_enabled: return
        icon = QSystemTrayIcon.MessageIcon.Information if success else QSystemTrayIcon.MessageIcon.Warning
        title = f"Análise Concluída: {host}:{port}" if success else f"Falha na Análise: {host}:{port}"
        msg = "Informações capturadas com sucesso." if success else "Não foi possível obter dados."
        self._tray.showMessage(title, msg, icon, 4000)

    def _on_traceroute_finished(self, host: str, hops: int, reached: bool):
        if not self._notif_enabled: return
        icon = QSystemTrayIcon.MessageIcon.Information if reached else QSystemTrayIcon.MessageIcon.Warning
        title = f"Traceroute Concluído: {host}" if reached else f"Traceroute Incompleto: {host}"
        msg = f"Destino alcançado em {hops} saltos." if reached else "Limite de saltos atingido sem alcançar o destino."
        self._tray.showMessage(title, msg, icon, 4000)

    def _on_mtr_finished(self, host: str, hops: int):
        if not self._notif_enabled: return
        icon = QSystemTrayIcon.MessageIcon.Information
        title = f"MTR Concluído: {host}"
        msg = "Todos os ciclos configurados foram finalizados."
        self._tray.showMessage(title, msg, icon, 4000)

    def _open_new_window(self):
        win = MainWindow()
        win.show()

    def _toggle_theme(self):
        new_dark = not self._is_dark
        apply_theme(QApplication.instance(), new_dark)
        for win in MainWindow._instances:
            win._is_dark = new_dark
            win._apply_window_theme()
            win._quick_ping.apply_theme(new_dark)
            for card in win._monitor._cards:
                card._graph.apply_theme(new_dark)

    def _update_status_bar(self):
        total, up, down = self._monitor.card_counts()
        self._lbl_hosts.setText(f"Hosts: {total}")
        self._lbl_up.setText(f"▲ Up: {up}")
        self._lbl_down.setText(f"▼ Down: {down}")

    def _save_screenshot(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar Screenshot", "nocping_screenshot.png",
            "Imagens (*.png *.jpg)",
        )
        if not path:
            return
        screen = QApplication.primaryScreen()
        px = screen.grabWindow(int(self.winId()))
        px.save(path)

    def _show_about(self):
        QMessageBox.about(
            self,
            "Sobre NOCPing",
            "<b>NOCPing</b><br>"
            "Ferramenta de diagnóstico de rede para analistas NOC.<br><br>"
            "Modos: TCP Ping · ICMP Ping · UDP Ping · Port Scan · Banner/TLS · Traceroute<br>"
            "Plataformas: Windows · macOS · Linux<br><br>"
            "<small>ICMP e UDP requerem privilégios de Administrador.</small>",
        )

    def closeEvent(self, event):
        QApplication.quit()

    def _shutdown(self):
        try:
            MainWindow._instances.remove(self)
        except ValueError:
            pass
        self._quick_ping.cleanup()
        for card in self._monitor._cards:
            card.stop()
        if self._scan:
            self._scan._cleanup_worker()
        if self._banner:
            self._banner._cleanup_worker()
        if self._traceroute and self._traceroute._worker and self._traceroute._worker.isRunning():
            self._traceroute._worker.stop()
            self._traceroute._worker.wait(500)
        if self._mtr and self._mtr._worker and self._mtr._worker.isRunning():
            self._mtr._worker.stop()
            self._mtr._worker.wait(500)
        # Fechar conexão SQLite do HistoryStore
        from core.history_store import HistoryStore
        HistoryStore.instance().close()

