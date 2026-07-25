"""
NOCPing — ui/widgets/tray.py
Ícone de bandeja do sistema — menu Abrir/Sair e restauração da janela.

As notificações de evento (host down/up, ping concluído, scan concluído...)
continuam decididas em MainWindow (é lógica de negócio de quando notificar,
não da bandeja em si) — este widget só encapsula o ícone/menu/restauração,
e permanece um QSystemTrayIcon de verdade, então `self._tray.showMessage(...)`
em MainWindow continua funcionando sem alteração.
"""
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QMainWindow
from PyQt6.QtGui import QIcon


class SystemTray(QSystemTrayIcon):
    def __init__(self, icon: QIcon, window: QMainWindow):
        super().__init__(icon, window)
        self._window = window

        menu = QMenu()
        act_show = menu.addAction("Abrir NOCPing")
        act_show.triggered.connect(self._restore_window)
        menu.addSeparator()
        act_quit = menu.addAction("Sair")
        act_quit.triggered.connect(QApplication.quit)

        self.setContextMenu(menu)
        self.setToolTip("NOCPing")
        self.activated.connect(self._on_activated)
        self.show()

    def _restore_window(self):
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._restore_window()
