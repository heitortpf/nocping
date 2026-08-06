"""
NOCPing — main.py
Entry point: inicializa Qt e abre a janela principal.
"""
import os
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow, apply_theme, detect_system_dark

_ICON_PATH = os.path.join(os.path.dirname(__file__), "NOCPing.ico")


def _set_windows_app_id():
    """No Windows, a barra de tarefas agrupa/escolhe o ícone de uma janela
    pelo AppUserModelID do processo, não só pelo QIcon da janela. Sem definir
    um explicitamente, o processo herda o ID (e às vezes o ícone genérico)
    do host que o lançou -- python.exe rodando via `python main.py`, ou o
    bootloader do PyInstaller num build --onefile. `setWindowIcon()` sozinho
    não é suficiente nesse caso. Precisa rodar antes de criar a QApplication.
    Não-Windows: no-op (a chamada nem existe fora de `ctypes.windll`)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("NOCPing.NOCPing.App")
    except Exception:
        pass


def main():
    _set_windows_app_id()

    # Necessário para HiDPI no Windows/Linux
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("NOCPing")
    app.setOrganizationName("NOCPing")
    if os.path.exists(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))

    apply_theme(app, detect_system_dark())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
