# 張詠鈞的python工作區
# File: 職缺搜尋器
# Created: 2026/1/3 上午 10:13

# area_mapper.py
# 將使用者輸入的中文縣市（台北/臺北/台北市/新竹/嘉義…）
# 轉換成 104 的 area 代碼（例如 6001001000）
#
# 依據 104「地區找工作」頁面自動抓取縣市清單與代碼，並快取到本機 json 檔。
# 建議：低頻使用（例如每日一次），避免對網站造成負擔。
# area_mapper.py
# 中文縣市 -> 104 area 代碼
# - 優先：線上抓取 104「地區找工作」頁面的縣市連結（帶 area 的頁面較穩）
# - 備援：內建台灣縣市代碼（線上抓不到也能正常轉換）
# job_db.py
# SQLite 資料庫模組：寫入每日快照 + 查詢昨天/今天新增/消失
# 依賴：標準庫 sqlite3（不用額外安裝）

import os
import sqlite3
import datetime
from typing import Dict, List, Tuple, Optional


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "db", "jobs.db")


def _ensure_dir(db_path: str) -> None:
    d = os.path.dirname(db_path)
    if d:
        os.makedirs(d, exist_ok=True)


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,      -- YYYY-MM-DD
                snapshot_time TEXT NOT NULL,      -- YYYY-MM-DD HH:MM
                keyword TEXT NOT NULL,
                areas TEXT NOT NULL,              -- 例如 台北市,新北市
                job_id TEXT NOT NULL,
                title TEXT,
                company TEXT,
                location TEXT,
                salary_text TEXT,
                post_date TEXT,
                url TEXT,
                UNIQUE(snapshot_date, keyword, areas, job_id)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_date ON job_snapshot(snapshot_date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_job_id ON job_snapshot(job_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kw_area ON job_snapshot(keyword, areas);")
        conn.commit()
    finally:
        conn.close()


def insert_snapshot_rows(
    rows: List[Dict[str, str]],
    keyword: str,
    areas: str,
    snapshot_time: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> int:
    """
    rows: normalize_jobs() 的結果（每筆至少要有 job_id/title/company/location/salary_text/post_date/url）
    keyword, areas: 這次搜尋條件
    snapshot_time: YYYY-MM-DD HH:MM（不傳就用現在時間）
    回傳：實際新增筆數（忽略重複）
    """
    init_db(db_path)

    if snapshot_time is None:
        snapshot_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    snapshot_date = snapshot_time.split(" ")[0]

    # 將每列補上共同欄位
    payload = []
    for r in rows:
        job_id = (r.get("job_id") or "").strip()
        if not job_id:
            continue
        payload.append({
            "snapshot_date": snapshot_date,
            "snapshot_time": snapshot_time,
            "keyword": keyword,
            "areas": areas,
            "job_id": job_id,
            "title": (r.get("title") or "").strip(),
            "company": (r.get("company") or "").strip(),
            "location": (r.get("location") or "").strip(),
            "salary_text": (r.get("salary_text") or "").strip(),
            "post_date": (r.get("post_date") or "").strip(),
            "url": (r.get("url") or "").strip(),
        })

    if not payload:
        return 0

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.executemany("""
            INSERT OR IGNORE INTO job_snapshot
            (snapshot_date, snapshot_time, keyword, areas, job_id, title, company, location, salary_text, post_date, url)
            VALUES
            (:snapshot_date, :snapshot_time, :keyword, :areas, :job_id, :title, :company, :location, :salary_text, :post_date, :url);
        """, payload)
        conn.commit()
        # 注意：sqlite 的 rowcount 對 executemany 可能不完全可靠，但通常足夠當「新增筆數」參考
        return cur.rowcount if cur.rowcount is not None else 0
    finally:
        conn.close()


def get_job_ids_for_day(keyword: str, areas: str, snapshot_date: str, db_path: str = DEFAULT_DB_PATH) -> List[str]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT job_id
            FROM job_snapshot
            WHERE snapshot_date = ? AND keyword = ? AND areas = ?;
        """, (snapshot_date, keyword, areas))
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def diff_today_yesterday(
    keyword: str,
    areas: str,
    today: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH
) -> Tuple[List[str], List[str], str, str]:
    """
    回傳：new_ids, removed_ids, today_date, yesterday_date
    new_ids: 今天有、昨天沒有
    removed_ids: 昨天有、今天沒有
    """
    if today is None:
        today_date = datetime.date.today().strftime("%Y-%m-%d")
    else:
        today_date = today

    y_date = (datetime.datetime.strptime(today_date, "%Y-%m-%d").date() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    today_ids = set(get_job_ids_for_day(keyword, areas, today_date, db_path))
    y_ids = set(get_job_ids_for_day(keyword, areas, y_date, db_path))

    new_ids = sorted(list(today_ids - y_ids))
    removed_ids = sorted(list(y_ids - today_ids))
    return new_ids, removed_ids, today_date, y_date


def fetch_jobs_by_ids(job_ids: List[str], db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, str]]:
    """
    用 job_id 抓回最新一筆資料（用 snapshot_time 最大）
    方便你做 NEW/REMOVED 報表時顯示 title/company/salary/url
    """
    if not job_ids:
        return []

    init_db(db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # 逐筆查最新（簡單穩，專題量不大）
        out: List[Dict[str, str]] = []
        for jid in job_ids:
            cur.execute("""
                SELECT job_id, title, company, location, salary_text, post_date, url, snapshot_time
                FROM job_snapshot
                WHERE job_id = ?
                ORDER BY snapshot_time DESC
                LIMIT 1;
            """, (jid,))
            row = cur.fetchone()
            if not row:
                continue
            out.append({
                "job_id": row[0],
                "title": row[1] or "",
                "company": row[2] or "",
                "location": row[3] or "",
                "salary_text": row[4] or "",
                "post_date": row[5] or "",
                "url": row[6] or "",
                "snapshot_time": row[7] or "",
            })
        return out
    finally:
        conn.close()


