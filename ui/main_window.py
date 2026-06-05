"""
NOCPing — ui/main_window.py
Janela principal com abas, menu e barra de status.
"""
import base64

from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget,
    QLabel, QMessageBox, QPushButton, QApplication, QFileDialog,
    QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import QSettings, QByteArray, QBuffer, QIODevice
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QAction, QPalette, QColor, QPainter, QPixmap, QPolygonF

from .monitor_tab import MonitorTab
from core.network import is_admin


DARK_PALETTE = {
    QPalette.ColorRole.Window:          "#11111b",
    QPalette.ColorRole.WindowText:      "#cdd6f4",
    QPalette.ColorRole.Base:            "#181825",
    QPalette.ColorRole.AlternateBase:   "#1e1e2e",
    QPalette.ColorRole.Text:            "#cdd6f4",
    QPalette.ColorRole.Button:          "#313244",
    QPalette.ColorRole.ButtonText:      "#cdd6f4",
    QPalette.ColorRole.Mid:             "#45475a",
    QPalette.ColorRole.Highlight:       "#7c3aed",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.ToolTipBase:     "#313244",
    QPalette.ColorRole.ToolTipText:     "#cdd6f4",
    QPalette.ColorRole.PlaceholderText: "#6b7280",
    QPalette.ColorRole.Link:            "#89b4fa",
}

LIGHT_PALETTE = {
    QPalette.ColorRole.Window:          "#eff1f5",
    QPalette.ColorRole.WindowText:      "#4c4f69",
    QPalette.ColorRole.Base:            "#ffffff",
    QPalette.ColorRole.AlternateBase:   "#e6e9ef",
    QPalette.ColorRole.Text:            "#4c4f69",
    QPalette.ColorRole.Button:          "#dce0e8",
    QPalette.ColorRole.ButtonText:      "#4c4f69",
    QPalette.ColorRole.Mid:             "#bcc0cc",
    QPalette.ColorRole.Highlight:       "#7c3aed",
    QPalette.ColorRole.HighlightedText: "#ffffff",
    QPalette.ColorRole.ToolTipBase:     "#dce0e8",
    QPalette.ColorRole.ToolTipText:     "#4c4f69",
    QPalette.ColorRole.PlaceholderText: "#9ca3af",
    QPalette.ColorRole.Link:            "#1d4ed8",
}

_arrow_cache: dict[str, str] = {}


def _arrow_url(direction: str, dark: bool) -> str:
    key = f"{direction}_{'dark' if dark else 'light'}"
    if key in _arrow_cache:
        return _arrow_cache[key]

    color = QColor("#cdd6f4" if dark else "#4c4f69")
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

    if dark:
        field_bg  = "#313244"; field_fg  = "#cdd6f4"
        border    = "#45475a"; focus_border = "#7c3aed"
        btn_bg    = "#45475a"; btn_hover = "#585b70"; btn_press = "#6c7086"
        scroll_bg = "#1e1e2e"; scroll_h  = "#45475a"
        tab_bg    = "#1e1e2e"; tab_fg    = "#9ca3af"; tab_fg_sel = "#cdd6f4"
        pane_b    = "#313244"; splitter  = "#313244"
        tip_fg    = "#cdd6f4"; tip_bg    = "#313244"
        sel_bg    = "#7c3aed"
    else:
        field_bg  = "#ffffff"; field_fg  = "#4c4f69"
        border    = "#bcc0cc"; focus_border = "#7c3aed"
        btn_bg    = "#dce0e8"; btn_hover = "#c8ccd4"; btn_press = "#bcc0cc"
        scroll_bg = "#e6e9ef"; scroll_h  = "#bcc0cc"
        tab_bg    = "#e6e9ef"; tab_fg    = "#9ca3af"; tab_fg_sel = "#4c4f69"
        pane_b    = "#bcc0cc"; splitter  = "#dce0e8"
        tip_fg    = "#4c4f69"; tip_bg    = "#dce0e8"
        sel_bg    = "#7c3aed"

    return f"""
    QToolTip {{ color:{tip_fg}; background:{tip_bg}; border:1px solid {border}; }}
    QTabWidget::pane {{ border:1px solid {pane_b}; }}
    QTabBar::tab {{
        background:{tab_bg}; color:{tab_fg}; padding:6px 16px;
        border-bottom:2px solid transparent;
    }}
    QTabBar::tab:selected {{ color:{tab_fg_sel}; border-bottom:2px solid #7c3aed; }}
    QTabBar::tab:hover:!selected {{ color:{tab_fg_sel}; }}
    QLineEdit, QComboBox {{
        background:{field_bg}; color:{field_fg}; border:1px solid {border};
        border-radius:4px; padding:3px 6px;
        selection-background-color:{sel_bg}; selection-color:#ffffff;
    }}
    QLineEdit:focus, QComboBox:focus {{ border:1px solid {focus_border}; }}
    QSpinBox {{
        background:{field_bg}; color:{field_fg}; border:1px solid {border};
        border-radius:4px; padding:3px 6px;
        selection-background-color:{sel_bg}; selection-color:#ffffff;
    }}
    QSpinBox:focus {{ border:1px solid {focus_border}; }}
    QSpinBox::up-button {{
        subcontrol-origin: border; subcontrol-position: top right;
        width:18px; background:{btn_bg};
        border-left:1px solid {border}; border-top-right-radius:4px;
    }}
    QSpinBox::up-button:hover   {{ background:{btn_hover}; }}
    QSpinBox::up-button:pressed {{ background:{btn_press}; }}
    QSpinBox::down-button {{
        subcontrol-origin: border; subcontrol-position: bottom right;
        width:18px; background:{btn_bg};
        border-left:1px solid {border}; border-bottom-right-radius:4px;
    }}
    QSpinBox::down-button:hover   {{ background:{btn_hover}; }}
    QSpinBox::down-button:pressed {{ background:{btn_press}; }}
    QSpinBox::up-arrow   {{ image: url({up});   width:8px; height:8px; }}
    QSpinBox::down-arrow {{ image: url({down}); width:8px; height:8px; }}
    QScrollBar:vertical {{ background:{scroll_bg}; width:8px; border-radius:4px; }}
    QScrollBar::handle:vertical {{ background:{scroll_h}; border-radius:4px; min-height:20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
    QScrollBar:horizontal {{ background:{scroll_bg}; height:8px; border-radius:4px; }}
    QScrollBar::handle:horizontal {{ background:{scroll_h}; border-radius:4px; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width:0; }}
    QSplitter::handle {{ background:{splitter}; }}
"""

DARK_MENUBAR_STYLE = (
    "QMenuBar{background:#11111b;color:#cdd6f4;}"
    "QMenuBar::item:selected{background:#313244;}"
    "QMenu{background:#1e1e2e;color:#cdd6f4;border:1px solid #313244;}"
    "QMenu::item:selected{background:#313244;}"
)

LIGHT_MENUBAR_STYLE = (
    "QMenuBar{background:#eff1f5;color:#4c4f69;}"
    "QMenuBar::item:selected{background:#dce0e8;}"
    "QMenu{background:#ffffff;color:#4c4f69;border:1px solid #bcc0cc;}"
    "QMenu::item:selected{background:#e6e9ef;}"
)

DARK_STATUSBAR_STYLE  = "QStatusBar{background:#11111b;color:#6b7280;font-size:11px;}"
LIGHT_STATUSBAR_STYLE = "QStatusBar{background:#eff1f5;color:#6b7280;font-size:11px;}"


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
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._monitor = MonitorTab()
        self._monitor.status_changed.connect(self._update_status_bar)
        self._monitor.host_status_changed.connect(self._on_host_status_changed)
        self._scan:       "ScanTab | None"       = None
        self._banner:     "BannerTab | None"     = None
        self._traceroute: "TracerouteTab | None" = None
        self._mtr:        "MTRTab | None"        = None
        self._initialized_tabs: set[int] = {0}

        self._tabs.addTab(self._monitor, "⬤  Monitor")
        self._tabs.addTab(QWidget(),     "🔍  Port Scan")
        self._tabs.addTab(QWidget(),     "🔒  Banner / TLS")
        self._tabs.addTab(QWidget(),     "📡  Traceroute")
        self._tabs.addTab(QWidget(),     "📊  MTR")
        self.setCentralWidget(self._tabs)
        self._tabs.currentChanged.connect(self._on_tab_activated)

    def _on_tab_activated(self, index: int):
        if index in self._initialized_tabs:
            return
        self._initialized_tabs.add(index)

        if index == 1:
            from .scan_tab import ScanTab
            self._scan = ScanTab()
            widget, label = self._scan, "🔍  Port Scan"
        elif index == 2:
            from .banner_tab import BannerTab
            self._banner = BannerTab()
            widget, label = self._banner, "🔒  Banner / TLS"
        elif index == 3:
            from .traceroute_tab import TracerouteTab
            self._traceroute = TracerouteTab()
            widget, label = self._traceroute, "📡  Traceroute"
        elif index == 4:
            from .mtr_tab import MTRTab
            self._mtr = MTRTab()
            widget, label = self._mtr, "📊  MTR"
        else:
            return

        self._tabs.currentChanged.disconnect(self._on_tab_activated)
        self._tabs.removeTab(index)
        self._tabs.insertTab(index, widget, label)
        self._tabs.setCurrentIndex(index)
        self._tabs.currentChanged.connect(self._on_tab_activated)

    def _build_status_bar(self):
        self._status_bar = self.statusBar()

        self._lbl_hosts = QLabel("Hosts: 0")
        self._lbl_up    = QLabel("▲ Up: 0")
        self._lbl_down  = QLabel("▼ Down: 0")
        self._lbl_admin = QLabel()

        self._lbl_up.setStyleSheet("color:#4ade80;")
        self._lbl_down.setStyleSheet("color:#f87171;")

        _admin = is_admin()
        admin_txt   = "🔐 Admin" if _admin else "⚠ Sem Admin (ICMP/UDP indisponível)"
        admin_color = "#4ade80"  if _admin else "#facc15"
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
        icon = self.windowIcon()
        self._tray = QSystemTrayIcon(icon, self)

        tray_menu = QMenu()
        act_show = tray_menu.addAction("Abrir NOCPing")
        act_show.triggered.connect(self._show_from_tray)
        tray_menu.addSeparator()
        act_quit = tray_menu.addAction("Sair")
        act_quit.triggered.connect(QApplication.quit)

        self._tray.setContextMenu(tray_menu)
        self._tray.setToolTip("NOCPing")
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

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

    def _open_new_window(self):
        win = MainWindow()
        win.show()

    def _toggle_theme(self):
        new_dark = not self._is_dark
        apply_theme(QApplication.instance(), new_dark)
        for win in MainWindow._instances:
            win._is_dark = new_dark
            win._apply_window_theme()
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
        if QSystemTrayIcon.isSystemTrayAvailable() and self._tray.isVisible():
            self.hide()
            event.ignore()
            return
        QApplication.quit()

    def _shutdown(self):
        try:
            MainWindow._instances.remove(self)
        except ValueError:
            pass
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

