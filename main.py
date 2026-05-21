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


def main():
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
