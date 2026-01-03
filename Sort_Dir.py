# 張詠鈞的python工作區
# File: Sort_Dir
# Created: 2026/1/3 下午 12:00

from pathlib import Path
import shutil
from datetime import datetime

# 以「此檔案所在資料夾」為基準，避免 PyCharm 工作目錄不同導致找不到
HERE = Path(__file__).resolve().parent

BASE_DIR = HERE / "台銀匯率網"
CSV_DIR = BASE_DIR / "台銀匯率CSV"
HTML_DIR = BASE_DIR / "台銀匯率HTML"


def ensure_folders():
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)


def safe_move(src: Path, dst_dir: Path) -> Path:
    """移動檔案；若目的地同名就自動加時間避免覆蓋"""
    dst = dst_dir / src.name
    if dst.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = dst_dir / f"{src.stem}_{ts}{src.suffix}"
    shutil.move(str(src), str(dst))
    return dst


def sort_existing_files(search_dir: Path) -> int:
    """把 search_dir 底下的 csv/html 檔案歸類移動"""
    ensure_folders()
    moved = 0

    # CSV
    for p in search_dir.glob("*.csv"):
        if p.parent != CSV_DIR:
            safe_move(p, CSV_DIR)
            moved += 1

    # HTML / HTM
    for p in list(search_dir.glob("*.html")) + list(search_dir.glob("*.htm")):
        if p.parent != HTML_DIR:
            safe_move(p, HTML_DIR)
            moved += 1

    return moved


if __name__ == "__main__":
    moved = sort_existing_files(HERE)

    print(f"[OK] 建立/確認資料夾：{BASE_DIR}")
    print(f"[OK] CSV 目錄：{CSV_DIR}")
    print(f"[OK] HTML 目錄：{HTML_DIR}")
    print(f"[OK] 本次移動檔案數：{moved}")

