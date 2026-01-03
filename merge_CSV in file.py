# 張詠鈞的python工作區
# File: merge_CSV in file
# Created: 2026/1/3 下午 02:30

from pathlib import Path
from datetime import datetime
import csv

from Sort_Dir import CSV_DIR


def merge_csvs(csv_dir: Path) -> Path:
    csv_dir = Path(csv_dir)

    if not csv_dir.exists():
        raise FileNotFoundError(f"CSV 目錄不存在：{csv_dir}")

    files = sorted([p for p in csv_dir.glob("*.csv") if p.is_file()])
    # 排除之前生成的合併檔
    files = [p for p in files if not p.name.endswith("_合併.csv")]

    if not files:
        raise FileNotFoundError(f"CSV 目錄內沒有可合併的 .csv：{csv_dir}")

    ts = datetime.now().strftime("%Y-%m-%d %H%M%S")
    out_path = csv_dir / f"{ts}_合併.csv"

    header_written = False
    written_rows = 0

    with out_path.open("w", newline="", encoding="utf-8-sig") as fout:
        writer = csv.writer(fout)

        for f in files:
            with f.open("r", newline="", encoding="utf-8-sig") as fin:
                reader = csv.reader(fin)
                first = True
                for row in reader:
                    if not row:
                        continue

                    # 第一列視為表頭：只寫一次
                    if first:
                        first = False
                        if not header_written:
                            writer.writerow(row)
                            header_written = True
                        continue

                    writer.writerow(row)
                    written_rows += 1

    print(f"[OK] 合併完成：{out_path}")
    print(f"[OK] 合併來源檔數：{len(files)}")
    print(f"[OK] 寫入資料列數：{written_rows}")
    return out_path


if __name__ == "__main__":
    merge_csvs(CSV_DIR)
