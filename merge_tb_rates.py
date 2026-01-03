# 張詠鈞的python工作區
# File: merge_tb_rates.py
# Created: 2026/1/3 下午 02:37
from pathlib import Path
from datetime import datetime
import csv
import re
import hashlib
from collections import defaultdict, Counter

HERE = Path(__file__).resolve().parent
CSV_DIR = HERE / "台銀匯率網" / "台銀匯率CSV"

# 只合併：YYYYMMDD_台銀匯率試算表*.csv
NAME_RE = re.compile(r"^(?P<yyyymmdd>\d{8})_台銀匯率試算表.*\.csv$", re.IGNORECASE)

# 幣別常見：USD / 美元(USD) / USD (美元) 之類
CCY_RE = re.compile(r"\b([A-Z]{3})\b")

BASELINE_FILES = CSV_DIR / "_baseline_files.csv"
BASELINE_ROWS = CSV_DIR / "_baseline_rows.csv"


def date_from_filename(name: str) -> str:
    m = NAME_RE.match(name)
    if not m:
        raise ValueError(f"檔名不符合規則：{name}")
    s = m.group("yyyymmdd")
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def open_csv(path: Path):
    """先 utf-8-sig，失敗再 cp950（Big5）"""
    try:
        f = path.open("r", newline="", encoding="utf-8-sig")
        return f, csv.reader(f)
    except UnicodeDecodeError:
        f = path.open("r", newline="", encoding="cp950", errors="replace")
        return f, csv.reader(f)


def norm_row(row):
    """去掉前後空白 + 去掉尾端連續空欄（行尾多逗號常見）"""
    r = [(c or "").strip() for c in row]
    while r and r[-1] == "":
        r.pop()
    return r


def sha256_bytes_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(lines) -> str:
    """對一串「已標準化的文字行」做 sha256（用 \n 串起來）"""
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def fingerprint_row(cells) -> str:
    """對整列內容做指紋（任一欄被改就會變）"""
    s = "|".join((c or "").strip() for c in cells)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def normalize_ccy(cell0: str) -> str:
    t = (cell0 or "").strip()
    m = CCY_RE.search(t)
    return m.group(1) if m else t


def load_baseline_files():
    """
    key = filename
    value = dict with:
      date, file_sha256, header_sha256, data_sha256, size_bytes, mtime_iso, rows
    """
    data = {}
    if not BASELINE_FILES.exists():
        return data

    with BASELINE_FILES.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            fn = (row.get("filename") or "").strip()
            if not fn:
                continue
            data[fn] = row
    return data


def load_baseline_rows():
    """
    key = (date, ccy)
    value = Counter of row_sha256 (允許同 key 出現多筆)
    """
    m = defaultdict(Counter)
    if not BASELINE_ROWS.exists():
        return m

    with BASELINE_ROWS.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            d = (row.get("date") or "").strip()
            ccy = (row.get("ccy") or "").strip()
            h = (row.get("row_sha256") or "").strip()
            if d and ccy and h:
                m[(d, ccy)][h] += 1
    return m


def append_baseline_files(rows_to_append):
    """rows_to_append: list[dict]"""
    need_header = not BASELINE_FILES.exists()
    with BASELINE_FILES.open("a", newline="", encoding="utf-8-sig") as f:
        fieldnames = [
            "date", "filename",
            "file_sha256", "header_sha256", "data_sha256",
            "size_bytes", "mtime_iso", "data_rows",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if need_header:
            w.writeheader()
        for row in rows_to_append:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def append_baseline_rows(rows_to_append):
    """rows_to_append: list[dict]"""
    need_header = not BASELINE_ROWS.exists()
    with BASELINE_ROWS.open("a", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["date", "ccy", "row_sha256", "filename", "row_index", "col_count"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if need_header:
            w.writeheader()
        for row in rows_to_append:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def merge_tb_csvs() -> Path:
    if not CSV_DIR.exists():
        raise FileNotFoundError(f"找不到 CSV 目錄：{CSV_DIR}")

    src_files = [p for p in CSV_DIR.glob("*.csv") if NAME_RE.match(p.name)]
    src_files.sort(key=lambda p: p.name)

    if not src_files:
        raise FileNotFoundError(f"沒有符合檔名「YYYYMMDD_台銀匯率試算表*.csv」的檔案：{CSV_DIR}")

    ts = datetime.now().strftime("%Y-%m-%d %H%M%S")
    out_path = CSV_DIR / f"{ts}_合併.csv"
    report_path = CSV_DIR / f"{ts}_合併_報告.txt"

    baseline_files = load_baseline_files()
    baseline_rows = load_baseline_rows()

    report = []
    report.append(f"[INFO] 合併輸出：{out_path.name}")
    report.append(f"[INFO] 來源檔數：{len(src_files)}")

    # 用第一個檔案的表頭當合併表頭（只寫一次）
    first_header = None
    header_ref_file = None

    # baseline 追加用（只新增 NEW 檔案，不覆蓋舊 baseline）
    baseline_files_append = []
    baseline_rows_append = []

    total_rows_written = 0
    tamper_files = []   # list of (filename, reason)
    schema_warns = 0

    # 供「檔內部同 key 不一致」提醒（額外，不影響 baseline）
    key_fps_current = defaultdict(Counter)

    with out_path.open("w", newline="", encoding="utf-8-sig") as fout:
        w = csv.writer(fout)

        for fpath in src_files:
            d = date_from_filename(fpath.name)

            # === 讀取 + 標準化 ===
            fin, reader = open_csv(fpath)
            with fin:
                raw_rows = [norm_row(r) for r in reader if r and any((c or "").strip() for c in r)]

            if not raw_rows:
                report.append(f"[WARN] {fpath.name} 內容空白，略過")
                continue

            header = raw_rows[0]
            data_rows = raw_rows[1:]

            # 統計欄位數範圍
            lens = [len(r) for r in data_rows] if data_rows else []
            min_len = min(lens) if lens else 0
            max_len = max(lens) if lens else 0
            report.append(f"[INFO] 檔案={fpath.name} 日期={d} 資料列={len(data_rows)} 欄位數範圍={min_len}..{max_len}")

            # === 合併檔表頭：只寫一次 ===
            if first_header is None:
                first_header = header
                header_ref_file = fpath.name
                w.writerow(["日期"] + first_header)
            else:
                if header != first_header:
                    schema_warns += 1
                    report.append(
                        f"[WARN] 表頭不一致：{fpath.name} 與 {header_ref_file} 不同（已略過此檔表頭，只合併資料列）"
                    )

            # === 指紋：file / header / data ===
            file_sha = sha256_bytes_of_file(fpath)
            header_sha = hashlib.sha256(("|".join(header)).encode("utf-8")).hexdigest()

            # data_sha：用「加入日期後的列」做 hash（確保任何數值變動都會影響）
            data_lines_for_hash = []
            for r in data_rows:
                data_lines_for_hash.append("|".join([d] + r))
            data_sha = sha256_text(data_lines_for_hash)

            stat = fpath.stat()
            size_bytes = str(stat.st_size)
            mtime_iso = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

            # === baseline 檢查（不自動覆蓋） ===
            base = baseline_files.get(fpath.name)
            if base is None:
                # NEW：寫入 baseline（允許新增）
                report.append(f"[NEW] {fpath.name} 尚無 baseline，已加入 baseline（首次建立/新日期檔案）")
                baseline_files_append.append({
                    "date": d,
                    "filename": fpath.name,
                    "file_sha256": file_sha,
                    "header_sha256": header_sha,
                    "data_sha256": data_sha,
                    "size_bytes": size_bytes,
                    "mtime_iso": mtime_iso,
                    "data_rows": str(len(data_rows)),
                })
                # per-row baseline
                for idx, r in enumerate(data_rows, start=1):
                    ccy = normalize_ccy(r[0]) if len(r) >= 1 else ""
                    out_row = [d] + r
                    row_sha = fingerprint_row(out_row)
                    baseline_rows_append.append({
                        "date": d,
                        "ccy": ccy,
                        "row_sha256": row_sha,
                        "filename": fpath.name,
                        "row_index": str(idx),
                        "col_count": str(len(r)),
                    })
            else:
                # 已存在 baseline：比對
                base_file_sha = (base.get("file_sha256") or "").strip()
                base_header_sha = (base.get("header_sha256") or "").strip()
                base_data_sha = (base.get("data_sha256") or "").strip()

                if file_sha == base_file_sha:
                    report.append(f"[OK]  {fpath.name} 與 baseline 一致（檔案未變動）")
                else:
                    # file 變動：再判斷是 header-only 還是 data 真的變了
                    if data_sha == base_data_sha and header_sha != base_header_sha:
                        report.append(f"[TAMPER?] {fpath.name} 檔案指紋不同，但 data 指紋一致 → 可能只有表頭/格式變動")
                        tamper_files.append((fpath.name, "HEADER_CHANGE_ONLY"))
                    else:
                        report.append(f"[TAMPER] {fpath.name} data 指紋與 baseline 不一致 → 疑似資料被修改")
                        tamper_files.append((fpath.name, "DATA_CHANGED"))

                        # 用 baseline_rows 定位到「哪天哪個幣別」被改（最關鍵）
                        current_map = defaultdict(Counter)
                        for r in data_rows:
                            ccy = normalize_ccy(r[0]) if len(r) >= 1 else ""
                            out_row = [d] + r
                            current_map[(d, ccy)][fingerprint_row(out_row)] += 1

                        # baseline 取同一天的 keys
                        base_keys = {k for k in baseline_rows.keys() if k[0] == d}
                        curr_keys = set(current_map.keys())

                        missing_keys = sorted(base_keys - curr_keys)
                        extra_keys = sorted(curr_keys - base_keys)
                        common_keys = sorted(base_keys & curr_keys)

                        if missing_keys:
                            report.append(f"         [DIFF] baseline 有但現在缺少：{len(missing_keys)} 組（例：{missing_keys[:5]}）")
                        if extra_keys:
                            report.append(f"         [DIFF] baseline 沒有但現在新增：{len(extra_keys)} 組（例：{extra_keys[:5]}）")

                        changed = []
                        for k in common_keys:
                            if baseline_rows[k] != current_map[k]:
                                changed.append(k)

                        if changed:
                            report.append(f"         [DIFF] 同 key 內容不同（疑似被改）：{len(changed)} 組（列出前 10 組）")
                            for k in changed[:10]:
                                report.append(f"           - KEY={k} baseline_hashes={dict(baseline_rows[k])} now_hashes={dict(current_map[k])}")
                        else:
                            report.append(f"         [INFO] key 級別未定位到差異（可能是無法解析幣別欄或整體格式差異）")

                    report.append("         baseline 不會自動更新（避免把被改過的檔案當成新基準）")

            # === 合併寫入（照原樣，不管欄位數） ===
            for r in data_rows:
                w.writerow([d] + r)
                total_rows_written += 1

                # 檔內部一致性（同一天同幣別出現兩筆不同內容）
                ccy = normalize_ccy(r[0]) if len(r) >= 1 else ""
                out_row = [d] + r
                key_fps_current[(d, ccy)][fingerprint_row(out_row)] += 1

    # === 寫 baseline（只追加 NEW，不覆蓋） ===
    if baseline_files_append:
        append_baseline_files(baseline_files_append)
    if baseline_rows_append:
        append_baseline_rows(baseline_rows_append)

    # === 補充：檔內部同 key 不一致提醒（非 baseline、只是品質提示） ===
    internal_inconsistent = [(k, len(v)) for k, v in key_fps_current.items() if len(v) > 1 and k[1] != ""]
    internal_inconsistent.sort(key=lambda x: (x[0][0], x[0][1]))

    report.append("")
    report.append(f"[INFO] 合併寫入資料列：{total_rows_written}")
    report.append(f"[INFO] 表頭不一致提醒次數：{schema_warns}")
    report.append(f"[INFO] baseline NEW 追加：files={len(baseline_files_append)} rows={len(baseline_rows_append)}")

    if tamper_files:
        report.append("")
        report.append(f"[ALERT] 偵測到與 baseline 不一致的檔案：{len(tamper_files)}")
        for fn, reason in tamper_files:
            report.append(f"  - {fn} reason={reason}")
        report.append("  建議：刪除合併檔後，重新下載/重新產生該日期檔案；baseline 不會自動覆蓋。")
    else:
        report.append("")
        report.append("[OK] 所有已存在 baseline 的來源檔，均未偵測到資料變動（以 baseline 指紋判斷）")

    if internal_inconsistent:
        report.append("")
        report.append(f"[WARN] 檔內部同一天同幣別出現多種內容（可能混入不同版型/不同值）：{len(internal_inconsistent)} 組（列出前 20 組）")
        for (d, ccy), kinds in internal_inconsistent[:20]:
            report.append(f"  - KEY=({d}, {ccy}) 指紋種類={kinds}")
    else:
        report.append("")
        report.append("[OK] 未發現檔內部同一天同幣別內容不一致（內部一致性檢查）")

    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"[OK] 合併完成：{out_path}")
    print(f"[OK] 報告輸出：{report_path}")
    print(f"[OK] baseline：{BASELINE_FILES.name}, {BASELINE_ROWS.name}")
    return out_path


if __name__ == "__main__":
    merge_tb_csvs()




