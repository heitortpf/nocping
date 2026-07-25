"""
NOCPing — scripts/visual_regression.py
Roda take_shots.py (gera screenshots/{dark,light}/*.png in-process, ver
comentário no topo daquele arquivo) e compara pixel a pixel contra um
diretório de baseline, reportando qualquer imagem cuja % de pixels
diferentes ultrapasse um threshold configurável.

Usa QImage (já é dependência via PyQt6) em vez de introduzir Pillow como
dependência nova — numpy já está disponível transitivamente via pyqtgraph,
usado aqui só para vetorizar a comparação de buffers.

    python scripts/visual_regression.py
    python scripts/visual_regression.py --tolerance 5
    python scripts/visual_regression.py --baseline-dir docs/redesign/screenshots-post
    python scripts/visual_regression.py --skip-capture --save-diffs

ATENÇÃO sobre o baseline padrão (docs/baseline/screenshots-pre/): esse
diretório é o estado ANTES do redesign visual completo desta sessão —
comparar o app atual contra ele vai reportar toda imagem fora de tolerância
(medido: ~9-41% de pixels diferentes, variando por seção/tema), por design
— é exatamente o que o redesign mudou. Isso é o esperado/correto para
documentar "quanto o redesign mudou visualmente", mas não serve como gate
de regressão contínua daqui pra frente. Para
detectar regressões visuais futuras (o uso mais comum de um script com esse
nome), rode com `--baseline-dir docs/redesign/screenshots-post` — o último
estado pós-redesign confirmado como correto — e trate os arquivos daquele
diretório como o baseline "atual" a partir de agora, atualizando-os quando
uma mudança visual for intencional.

Exit code: 0 se todas as imagens ficaram dentro da tolerância, 1 caso
contrário (para uso em CI como gate).
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from PyQt6.QtGui import QImage

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_BASELINE_DIR = os.path.join("docs", "baseline", "screenshots-pre")
DEFAULT_OUT_DIR = "screenshots"
DEFAULT_TOLERANCE_PCT = 2.0
# Diferença mínima por canal (0-255) pra um pixel contar como "diferente" —
# ignora ruído de antialiasing/subpixel rendering entre capturas idênticas.
DEFAULT_PIXEL_EPSILON = 24

THEMES = ("dark", "light")
FILENAMES = (
    "quick_ping.png", "monitor.png", "portscan.png",
    "banner.png", "traceroute.png", "mtr.png",
)


def _load_rgba(path: str) -> "np.ndarray | None":
    img = QImage(path)
    if img.isNull():
        return None
    img = img.convertToFormat(QImage.Format.Format_RGBA8888)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    stride = img.bytesPerLine() // 4
    arr = np.frombuffer(bytes(ptr), dtype=np.uint8).reshape(img.height(), stride, 4)
    return arr[:, : img.width(), :]


def compare_images(current_path: str, baseline_path: str, epsilon: int):
    """Retorna (percentual_diferente, motivo) — motivo é None se a
    comparação pixel-a-pixel foi feita normalmente, ou uma string explicando
    por que não deu (arquivo ausente / dimensões diferentes)."""
    if not os.path.isfile(current_path):
        return 100.0, "screenshot atual ausente"
    if not os.path.isfile(baseline_path):
        return 100.0, "baseline ausente"

    cur = _load_rgba(current_path)
    base = _load_rgba(baseline_path)
    if cur is None or base is None:
        return 100.0, "falha ao decodificar PNG"
    if cur.shape != base.shape:
        return 100.0, f"dimensões diferentes ({cur.shape[1]}x{cur.shape[0]} vs {base.shape[1]}x{base.shape[0]})"

    diff = np.abs(cur.astype(np.int16) - base.astype(np.int16))
    changed = np.any(diff > epsilon, axis=2)
    pct = 100.0 * changed.sum() / changed.size
    return pct, None


def save_diff_image(current_path: str, baseline_path: str, out_path: str, epsilon: int):
    cur = _load_rgba(current_path)
    base = _load_rgba(baseline_path)
    if cur is None or base is None or cur.shape != base.shape:
        return
    diff = np.abs(cur.astype(np.int16) - base.astype(np.int16))
    changed = np.any(diff > epsilon, axis=2)

    out = cur.copy()
    out[changed] = [255, 0, 0, 255]  # vermelho sólido nos pixels que mudaram
    h, w, _ = out.shape
    img = QImage(out.tobytes(), w, h, w * 4, QImage.Format.Format_RGBA8888)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)


def run_take_shots() -> bool:
    print("Rodando take_shots.py para gerar screenshots atuais...\n")
    result = subprocess.run(
        [sys.executable, "take_shots.py"], cwd=_ROOT,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Compara screenshots atuais do NOCPing pixel a pixel contra um baseline.",
    )
    parser.add_argument("--baseline-dir", default=DEFAULT_BASELINE_DIR,
                         help=f"diretório com {{dark,light}}/*.png de referência (default: {DEFAULT_BASELINE_DIR})")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR,
                         help=f"diretório com {{dark,light}}/*.png atuais, gerado por take_shots.py (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE_PCT,
                         help=f"%% máxima de pixels diferentes tolerada por imagem (default: {DEFAULT_TOLERANCE_PCT})")
    parser.add_argument("--pixel-epsilon", type=int, default=DEFAULT_PIXEL_EPSILON,
                         help=f"diferença mínima por canal (0-255) pra contar um pixel como diferente (default: {DEFAULT_PIXEL_EPSILON})")
    parser.add_argument("--skip-capture", action="store_true",
                         help="não roda take_shots.py -- compara o que já existir em --out-dir")
    parser.add_argument("--save-diffs", action="store_true",
                         help="salva imagens de diff (pixels alterados em vermelho) em docs/redesign/visual-diffs/")
    args = parser.parse_args()

    if os.path.normpath(args.baseline_dir) == os.path.normpath(DEFAULT_BASELINE_DIR):
        print(
            "AVISO: comparando contra o baseline PRÉ-redesign "
            f"({DEFAULT_BASELINE_DIR}) -- espere diferenças bem acima da\n"
            "tolerância em toda imagem, por design (é o que o redesign visual\n"
            "desta sessão mudou). Pra detectar regressões visuais futuras, use:\n"
            "  --baseline-dir docs/redesign/screenshots-post\n"
        )

    if not args.skip_capture:
        if not run_take_shots():
            print("take_shots.py falhou -- abortando comparação.")
            return 1
    else:
        print(f"--skip-capture: comparando screenshots já existentes em {args.out_dir}/\n")

    rows = []
    diff_dir = os.path.join("docs", "redesign", "visual-diffs")
    for theme in THEMES:
        for filename in FILENAMES:
            current_path = os.path.join(args.out_dir, theme, filename)
            baseline_path = os.path.join(args.baseline_dir, theme, filename)
            pct, reason = compare_images(current_path, baseline_path, args.pixel_epsilon)
            status = "OK" if pct <= args.tolerance else "DIFF"
            rows.append((theme, filename, pct, status, reason))

            if args.save_diffs and reason is None and status == "DIFF":
                out_path = os.path.join(diff_dir, theme, filename)
                save_diff_image(current_path, baseline_path, out_path, args.pixel_epsilon)

    name_w = max(len(f"{t}/{f}") for t, f, *_ in rows)
    print(f"{'imagem':<{name_w}}  {'% diferente':>12}  status  motivo")
    print("-" * (name_w + 40))
    failures = 0
    for theme, filename, pct, status, reason in rows:
        label = f"{theme}/{filename}"
        marker = reason or ""
        if status == "DIFF":
            failures += 1
        print(f"{label:<{name_w}}  {pct:>11.2f}%  {status:<4}  {marker}")

    print(f"\n{len(rows) - failures}/{len(rows)} dentro da tolerância ({args.tolerance}%).")
    if args.save_diffs and failures:
        print(f"Diffs visuais salvos em {diff_dir}/")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
