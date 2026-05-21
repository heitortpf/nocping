"""
NOCPing — main.py
Entry point: inicializa Qt e abre a janela principal.
"""
import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow, apply_theme, detect_system_dark


def main():
    # Necessário para HiDPI no Windows/Linux
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("NOCPing")
    app.setOrganizationName("NOCPing")

    apply_theme(app, detect_system_dark())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
