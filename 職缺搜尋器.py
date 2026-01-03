# 張詠鈞的python工作區
# File: 職缺搜尋器
# Created: 2026/1/3 上午 10:13

# job_tracker_104.py
# 使用者輸入：關鍵字 + 中文縣市（可逗號多個）
# 程式自動轉成 104 area code -> 抓職缺 -> 存 CSV
#
# pip install requests beautifulsoup4
# job_tracker_104.py
# 104 職缺追蹤器（JSON 抓取）：
# 1) 使用者輸入：關鍵字 + 中文縣市（可逗號多個）
# 2) 自動轉成 area code
# 3) 抓職缺 -> 輸出 CSV
# 4) 寫入 SQLite（job_db.py）
# 5) 顯示「今天 vs 昨天」新增/消失

import csv
import datetime
import re
import time
from typing import Any, Dict, List

import requests

from area_mapper import resolve_area
import job_MSSQL_db as job_db


def now_tag() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M")


def safe_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[\\/:*?\"<>|]", "_", s)
    s = re.sub(r"\s+", "_", s)
    return s[:80] if len(s) > 80 else s


def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    })
    return s


def fetch_104_jobs_json(session: requests.Session, keyword: str, area_codes_csv: str, page: int = 1, timeout: int = 20) -> Dict[str, Any]:
    url = "https://www.104.com.tw/jobs/search/list"
    params = {
        "ro": "0",
        "keyword": keyword,
        "area": area_codes_csv,   # 例如 6001001000 或 6001001000,6001002000
        "page": str(page),
        "mode": "s",
        "order": "15",            # 最近更新（若未來失效可刪）
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.104.com.tw/jobs/search/",
    }

    r = session.get(url, params=params, headers=headers, timeout=timeout)

    if r.status_code == 403:
        raise RuntimeError("HTTP 403：104 阻擋此請求（通常降頻、稍後再試即可）。")

    r.raise_for_status()
    return r.json()


def normalize_jobs(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    data = payload.get("data") or {}
    items = data.get("list") or []

    rows: List[Dict[str, str]] = []

    for it in items:
        job_id = str(it.get("jobNo") or "").strip()
        if not job_id:
            continue

        title = str(it.get("jobName") or "").strip()
        company = str(it.get("custName") or "").strip()

        location = str(it.get("jobAddrNoDesc") or it.get("workAreaDesc") or it.get("jobAddress") or "").strip()
        salary_text = str(it.get("salaryDesc") or "").strip()
        post_date = str(it.get("appearDate") or it.get("updateDate") or "").strip()

        url = ""
        link = it.get("link")
        if isinstance(link, dict):
            job_link = link.get("job") or ""
            if isinstance(job_link, str):
                url = job_link if job_link.startswith("http") else ("https:" + job_link if job_link.startswith("//") else job_link)
        if not url:
            url = f"https://www.104.com.tw/job/{job_id}"

        rows.append({
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "salary_text": salary_text,
            "post_date": post_date,
            "url": url,
        })

    return rows


def write_csv(rows: List[Dict[str, str]], filepath: str, keyword: str, areas_text: str) -> None:
    fieldnames = [
        "keyword",
        "areas",
        "title",
        "company",
        "location",
        "salary_text",
        "post_date",
        "url",
        "job_id",
        "snapshot_time",
    ]
    snapshot_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "keyword": keyword,
                "areas": areas_text,
                "title": r["title"],
                "company": r["company"],
                "location": r["location"],
                "salary_text": r["salary_text"],
                "post_date": r["post_date"],
                "url": r["url"],
                "job_id": r["job_id"],
                "snapshot_time": snapshot_time,
            })

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=job_seek;"
    "UID=cim;"
    "PWD=1234;"
    "TrustServerCertificate=yes;"
)

def main() -> None:
    keyword = input("請輸入職缺關鍵字（例：C# / Python / 資料分析師）：").strip()
    areas_text = input("請輸入縣市地區（可逗號多個，例如：台北市,新北市 或 台北,新北）：").strip()

    if not keyword or not areas_text:
        print("[ERR] 關鍵字與地區不可為空")
        return

    # 解析多地區（中文）
    area_inputs = [a.strip() for a in areas_text.split(",") if a.strip()]
    try:
        resolved = [resolve_area(a) for a in area_inputs]
    except Exception as e:
        print(f"[ERR] 地區解析失敗：{e}")
        return

    area_codes_csv = ",".join(r.area_code for r in resolved)
    area_names = ",".join(r.matched_name for r in resolved)

    print(f"[INFO] 地區解析：{areas_text} -> {area_names} -> {area_codes_csv}")

    session = build_session()

    max_pages = 3          # 你可自行調整
    page_sleep = 1.2       # 低頻友善

    all_rows: List[Dict[str, str]] = []

    for page in range(1, max_pages + 1):
        try:
            payload = fetch_104_jobs_json(session, keyword=keyword, area_codes_csv=area_codes_csv, page=page)
        except Exception as e:
            print(f"[ERR] 抓取第 {page} 頁失敗：{e}")
            break

        rows = normalize_jobs(payload)
        if not rows:
            break

        all_rows.extend(rows)
        time.sleep(page_sleep)

    if not all_rows:
        print("[INFO] 沒抓到任何職缺（條件太嚴格或暫時被限制）。")
        return

    # 1) 輸出 CSV
    out_name = f"{now_tag()}_104_{safe_filename(keyword)}_{safe_filename(area_names)}.csv"
    write_csv(all_rows, out_name, keyword=keyword, areas_text=area_names)
    print(f"[OK] 已輸出 CSV：{out_name}")

    # 2) 寫入 DB（每日快照）
    inserted = job_db.insert_snapshot_rows(
        rows=all_rows,
        keyword=keyword,
        areas=area_names,
        conn_str=CONN_STR
    )
    print(f"[OK] DB 寫入完成（可能忽略重複）：{inserted} rows")

    # 3) 今天 vs 昨天差異
    new_ids, removed_ids, today_date, y_date = job_db.diff_today_yesterday(
        keyword=keyword,
        areas=area_names,
        conn_str=CONN_STR
    )
    print(f"[DIFF] {today_date} vs {y_date}：新增 {len(new_ids)}，消失 {len(removed_ids)}")

    # 4) 預覽前 10 筆（確認有在跑）
    print(f"[INFO] 共 {len(all_rows)} 筆，預覽前 10 筆：")
    for i, r in enumerate(all_rows[:10], start=1):
        print(f"{i:02d}. {r['title']} | {r['company']} | {r['salary_text']} | {r['location']}")

    # 5) 額外：列出新增職缺前 10 筆（可選）
    if new_ids:
        print("[NEW] 今日新增（前 10 筆）：")
        new_jobs = job_db.fetch_jobs_by_ids(new_ids,conn_str=CONN_STR)
        for j in new_jobs[:10]:
            print(f" - {j['title']} | {j['company']} | {j['salary_text']} | {j['url']}")


if __name__ == "__main__":
    main()

