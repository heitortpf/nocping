"""
NOCPing — take_shots.py
Gera screenshots de cada seção do app, nos dois temas, para screenshots/ e
docs/README.

Roda 100% in-process: instancia MainWindow numa QApplication real, navega
entre seções via MainWindow.show_section(name) (API única de navegação
programática — não depende de saber se a navegação hoje é sidebar,
QTabWidget ou outra coisa) e captura com QWidget.grab(), o mesmo tipo de
mecanismo in-process usado por MainWindow._save_screenshot() ("Salvar
Screenshot..." / Ctrl+P — ver CLAUDE.md, seção "Screenshot integrado").

Por que não capturar a tela real (win32gui/ImageGrab) nem clicar por
coordenada de pixel, como a versão antiga deste script fazia: (1) offsets de
clique fixos quebram toda vez que a navegação muda — foi exatamente isso que
quebrou aqui após a Quick Ping virar aba 0 (v1.3.0) e de novo quando a
navegação virou sidebar (Fase 3.7); (2) captura de tela real exige a janela
visível, no topo e sem sobreposição — QWidget.grab() renderiza o widget
diretamente, sem depender de foco/oclusão/estar realmente na tela.

Gera 12 imagens (6 seções × 2 temas) em screenshots/{dark,light}/<nome>.png.
"""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import MainWindow, apply_theme

OUT_DIR = "screenshots"

# nome da seção (MainWindow.SECTIONS) -> nome do arquivo de saída.
# Mantém os nomes de arquivo já usados no README (monitor.png, portscan.png,
# banner.png, traceroute.png, mtr.png) + quick_ping.png, que nunca existiu.
FILENAMES = {
    "quick_ping": "quick_ping.png",
    "monitor":    "monitor.png",
    "port_scan":  "portscan.png",
    "banner_tls": "banner.png",
    "traceroute": "traceroute.png",
    "mtr":        "mtr.png",
}


def _pump(app: QApplication, n: int = 10):
    for _ in range(n):
        app.processEvents()


def capture_theme(app: QApplication, dark: bool) -> list[str]:
    theme_dir = os.path.join(OUT_DIR, "dark" if dark else "light")
    os.makedirs(theme_dir, exist_ok=True)

    apply_theme(app, dark)
    win = MainWindow()
    win._is_dark = dark
    win._apply_window_theme()
    win.show()
    _pump(app)
    time.sleep(0.3)

    saved = []
    for section in MainWindow.SECTIONS:
        win.show_section(section)
        _pump(app)
        time.sleep(0.2)  # tempo pro RttGraph/pyqtgraph terminar o primeiro paint

        path = os.path.join(theme_dir, FILENAMES[section])
        win.grab().save(path)
        saved.append(path)
        print(f"salvo: {path}")

    win.close()
    _pump(app, 5)
    return saved


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("NOCPing")

    all_saved = []
    for dark in (True, False):
        all_saved += capture_theme(app, dark)

    print(f"\n{len(all_saved)} imagens geradas.")


if __name__ == "__main__":
    main()
