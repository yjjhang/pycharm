# 張詠鈞的python工作區
# File: merge_tb_rates.py
# Created: 2026/1/3 下午 02:37
from pathlib import Path
from datetime import datetime
import csv
import re

HERE = Path(__file__).resolve().parent
CSV_DIR = HERE / "台銀匯率網" / "台銀匯率CSV"

# 只合併：YYYYMMDD_台銀匯率試算表*.csv
NAME_RE = re.compile(r"^(?P<yyyymmdd>\d{8})_台銀匯率試算表.*\.csv$", re.IGNORECASE)


def _open_csv(path: Path):
    """先用 utf-8-sig，失敗再用 cp950（Big5）"""
    try:
        f = path.open("r", newline="", encoding="utf-8-sig")
        return f, csv.reader(f)
    except UnicodeDecodeError:
        f = path.open("r", newline="", encoding="cp950", errors="replace")
        return f, csv.reader(f)


def _date_from_filename(filename: str) -> str:
    """
    從檔名抓 YYYYMMDD -> 轉成 YYYY-MM-DD
    例如：20260103_台銀匯率試算表.csv -> 2026-01-03
    """
    m = NAME_RE.match(filename)
    if not m:
        raise ValueError(f"檔名不符合規則，無法取日期：{filename}")
    s = m.group("yyyymmdd")
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def merge_tb_csvs() -> Path:
    if not CSV_DIR.exists():
        raise FileNotFoundError(f"找不到 CSV 目錄：{CSV_DIR}")

    files = []
    for p in CSV_DIR.glob("*.csv"):
        if NAME_RE.match(p.name):
            files.append(p)
    files.sort(key=lambda p: p.name)

    if not files:
        raise FileNotFoundError(
            f"目錄內沒有符合檔名「YYYYMMDD_台銀匯率試算表*.csv」的 CSV：{CSV_DIR}"
        )

    out_name = datetime.now().strftime("%Y-%m-%d %H%M%S") + "_合併.csv"
    out_path = CSV_DIR / out_name

    header_written = False
    written_rows = 0

    with out_path.open("w", newline="", encoding="utf-8-sig") as fout:
        writer = csv.writer(fout)

        for fpath in files:
            file_date = _date_from_filename(fpath.name)

            fin, reader = _open_csv(fpath)
            with fin:
                first = True
                for row in reader:
                    if not row:
                        continue

                    # 第一列視為表頭：只寫一次，且最前面插入「日期」
                    if first:
                        first = False
                        if not header_written:
                            writer.writerow(["日期"] + row)
                            header_written = True
                        continue

                    # 資料列：最前面插入該檔案日期
                    writer.writerow([file_date] + row)
                    written_rows += 1

    print(f"[OK] 合併完成：{out_path}")
    print(f"[OK] 合併來源檔數：{len(files)}")
    print(f"[OK] 寫入資料列數：{written_rows}")
    return out_path


if __name__ == "__main__":
    merge_tb_csvs()


