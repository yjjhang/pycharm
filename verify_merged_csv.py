# 張詠鈞的python工作區
# File: verify_merged_csv.py
# Created: 2026/1/3 下午 03:23

from pathlib import Path
import csv
import re
import hashlib
from collections import Counter

HERE = Path(__file__).resolve().parent
CSV_DIR = HERE / "台銀匯率網" / "台銀匯率CSV"

NAME_RE = re.compile(r"^(?P<yyyymmdd>\d{8})_台銀匯率試算表.*\.csv$", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MERGED_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{6}_合併\.csv$", re.IGNORECASE)


def open_csv(path: Path):
    # 跟你合併程式一致：先 utf-8-sig，失敗 fallback cp950
    try:
        f = path.open("r", newline="", encoding="utf-8-sig")
        return f, csv.reader(f)
    except UnicodeDecodeError:
        f = path.open("r", newline="", encoding="cp950", errors="replace")
        return f, csv.reader(f)


def row_fingerprint(row):
    """
    將 row 轉成穩定字串後做 hash
    - strip 去空白
    - 以 | 串起來避免逗號干擾
    """
    s = "|".join((c or "").strip() for c in row)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def find_latest_merged(csv_dir: Path) -> Path:
    candidates = [p for p in csv_dir.glob("*_合併.csv") if MERGED_RE.match(p.name)]
    if not candidates:
        raise FileNotFoundError("找不到任何符合格式的合併檔：YYYY-MM-DD HHmmss_合併.csv")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def verify(merged_path: Path):
    # 1) 收集來源檔
    src_files = [p for p in CSV_DIR.glob("*.csv") if NAME_RE.match(p.name)]
    src_files.sort(key=lambda p: p.name)
    if not src_files:
        raise FileNotFoundError("沒有找到任何來源檔：YYYYMMDD_台銀匯率試算表*.csv")

    # 2) 讀合併檔：計數 + 指紋 + 結構檢查
    with merged_path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        merged_rows = list(reader)

    if not merged_rows:
        raise RuntimeError("合併檔是空的")

    merged_header = merged_rows[0]
    merged_data = merged_rows[1:]

    # 合併檔第一欄要是 日期
    if len(merged_header) < 2 or merged_header[0].strip() != "日期":
        raise RuntimeError(f"合併檔表頭不符合預期，第一欄應為「日期」：{merged_header}")

    expected_cols = len(merged_header)

    merged_bad_rows = []
    merged_fp = Counter()

    for idx, r in enumerate(merged_data, start=2):  # 從第2行開始（1-based）
        if len(r) != expected_cols:
            merged_bad_rows.append((idx, "欄位數不一致", r))
            continue
        if not DATE_RE.match(r[0].strip()):
            merged_bad_rows.append((idx, "日期格式錯誤", r))
            continue

        merged_fp[row_fingerprint(r)] += 1

    # 3) 讀來源檔：把每筆資料列加上日期後做同樣的指紋
    src_total_rows = 0
    src_fp = Counter()
    src_bad_rows = []

    for p in src_files:
        yyyymmdd = NAME_RE.match(p.name).group("yyyymmdd")
        file_date = f"{yyyymmdd[0:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"

        fin, reader = open_csv(p)
        with fin:
            header = next(reader, None)
            if header is None:
                continue

            for r in reader:
                if not r:
                    continue
                src_total_rows += 1

                # 合併檔是 ["日期"] + header，所以來源列也要變成 [date] + row 才能對比
                rr = [file_date] + r

                if len(rr) != expected_cols:
                    src_bad_rows.append((p.name, "欄位數不一致", rr))
                    continue

                src_fp[row_fingerprint(rr)] += 1

    # 4) 驗證結果：筆數、指紋集合
    merged_total_rows = len(merged_data)

    ok_count = (merged_total_rows == src_total_rows)
    ok_hash = (merged_fp == src_fp)

    print("===== 驗證結果 =====")
    print(f"[INFO] 來源檔數：{len(src_files)}")
    print(f"[INFO] 來源總資料列（不含表頭）：{src_total_rows}")
    print(f"[INFO] 合併總資料列（不含表頭）：{merged_total_rows}")
    print(f"[CHECK] 筆數一致：{ok_count}")
    print(f"[CHECK] 內容指紋一致：{ok_hash}")

    if merged_bad_rows:
        print(f"[WARN] 合併檔異常列數：{len(merged_bad_rows)}（顯示前 5 筆）")
        for item in merged_bad_rows[:5]:
            print("  -", item)

    if src_bad_rows:
        print(f"[WARN] 來源檔異常列數：{len(src_bad_rows)}（顯示前 5 筆）")
        for item in src_bad_rows[:5]:
            print("  -", item)

    # 若 hash 不一致，找出差異（可能漏列/多列/內容變了）
    if not ok_hash:
        diff = (src_fp - merged_fp)  # 來源有但合併沒有
        extra = (merged_fp - src_fp) # 合併多出來的
        print(f"[DIFF] 來源有但合併缺少的列數（以指紋計）：{sum(diff.values())}")
        print(f"[DIFF] 合併多出來的列數（以指紋計）：{sum(extra.values())}")

    if ok_count and ok_hash and not merged_bad_rows and not src_bad_rows:
        print("[OK] 驗證通過：無漏列、內容一致、欄位結構正常")


if __name__ == "__main__":
    merged = find_latest_merged(CSV_DIR)
    print(f"[INFO] 以最新合併檔進行驗證：{merged.name}")
    verify(merged)
