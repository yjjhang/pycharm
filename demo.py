# 張詠鈞的python工作區
# File: demo
# Created: 2026/1/10 上午 11:26
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""
demo.py - Compare 104 job search: BeautifulSoup(HTML) vs JSON list API

條件：
- keyword: Python工程師
- area: 6001005000 (桃園市)
- jobcat: 2007001004 (軟體工程師)

輸出：
- html_jobs.csv
- json_jobs.csv
- diff_report.txt
"""

import csv
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


HTML_PAGE_URL = (
    "https://www.104.com.tw/jobs/search/"
    "?area=6001005000&jobsource=joblist_search&keyword=Python%E5%B7%A5%E7%A8%8B%E5%B8%AB"
    "&mode=s&page=1&order=15&jobcat=2007001004"
)

JSON_LIST_API = "https://www.104.com.tw/jobs/search/list"
JSON_PARAMS = {
    "ro": 0,
    "kwop": 7,
    "keyword": "Python工程師",
    "area": "6001005000",
    "order": 15,
    "asc": 0,
    "page": 1,
    "mode": "s",
    "jobsource": "joblist_search",
    "jobcat": "2007001004",
    "expansionType": "area,spec,com,job,wf,wktm",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.104.com.tw/jobs/search/",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
}

JOB_ID_RE = re.compile(r"/job/([A-Za-z0-9]+)")


def extract_job_id(link: str) -> str:
    m = JOB_ID_RE.search(link or "")
    return m.group(1) if m else ""


def fetch_html_jobs(session: requests.Session, url: str) -> dict:
    r = session.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    jobs = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/job/" not in href:
            continue

        if href.startswith("//"):
            link = "https:" + href
        elif href.startswith("/"):
            link = urljoin("https://www.104.com.tw", href)
        else:
            link = href

        job_id = extract_job_id(link)
        if not job_id:
            continue

        title = a.get_text(strip=True) or a.get("title", "")
        jobs[job_id] = {"job_id": job_id, "title_from_html": title, "link": link}

    return jobs


def fetch_json_payload(session: requests.Session) -> dict:
    r = session.get(JSON_LIST_API, params=JSON_PARAMS, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()

    # ✅ 104 這邊有時 status=0、有時 status=200（都表示成功）
    status = data.get("status")
    status_str = str(status) if status is not None else ""

    if status_str not in ("0", "200"):
        raise RuntimeError(
            f"API not success. status={status} msg={data.get('statusMsg')} err={data.get('errorMsg')}"
        )

    return data


def parse_json_jobs(payload: dict) -> dict:
    """
    兼容不同回傳結構：
    - payload["data"]["list"]
    - payload["data"] 直接就是 list
    - payload["list"]
    """
    container = payload.get("data", payload)

    if isinstance(container, dict):
        items = container.get("list") or container.get("jobList") or container.get("jobs") or []
    elif isinstance(container, list):
        items = container
    else:
        items = []

    jobs = {}
    for it in items:
        if not isinstance(it, dict):
            continue

        link = it.get("link", "") or it.get("jobUrl", "") or ""
        if isinstance(link, str) and link.startswith("//"):
            link = "https:" + link

        job_id = it.get("jobNo") or extract_job_id(link)
        if not job_id:
            continue

        jobs[str(job_id)] = {
            "job_id": str(job_id),
            "jobName": it.get("jobName", "") or it.get("name", ""),
            "custName": it.get("custName", "") or it.get("company", ""),
            "salaryDesc": it.get("salaryDesc", "") or it.get("salary", ""),
            "jobAddr": it.get("jobAddrNoDesc", "") or it.get("jobAddress", "") or it.get("areaDesc", ""),
            "appearDate": it.get("appearDate", "") or it.get("updateDate", ""),
            "applyCnt": it.get("applyCnt", ""),
            "link": link or f"https://www.104.com.tw/job/{job_id}",
        }

    return jobs


def write_csv(path: str, rows: list, fieldnames: list):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main():
    with requests.Session() as s:
        html_jobs = fetch_html_jobs(s, HTML_PAGE_URL)

        payload = fetch_json_payload(s)
        json_jobs = parse_json_jobs(payload)

    html_ids = set(html_jobs.keys())
    json_ids = set(json_jobs.keys())
    overlap = html_ids & json_ids
    html_only = html_ids - json_ids
    json_only = json_ids - html_ids

    print("=== Compare Result (Python工程師 + 桃園市 + 軟體工程師) ===")
    print("HTML job count :", len(html_ids))
    print("JSON job count :", len(json_ids))
    print("Overlap        :", len(overlap))
    print("HTML only      :", len(html_only))
    print("JSON only      :", len(json_only))

    write_csv("html_jobs.csv", list(html_jobs.values()), ["job_id", "title_from_html", "link"])
    write_csv(
        "json_jobs.csv",
        list(json_jobs.values()),
        ["job_id", "jobName", "custName", "salaryDesc", "jobAddr", "appearDate", "applyCnt", "link"],
    )

    with open("diff_report.txt", "w", encoding="utf-8") as f:
        f.write("=== Conditions ===\n")
        f.write("keyword=Python工程師\narea=6001005000(桃園市)\njobcat=2007001004(軟體工程師)\n\n")

        f.write("=== Summary ===\n")
        f.write(f"HTML job count : {len(html_ids)}\n")
        f.write(f"JSON job count : {len(json_ids)}\n")
        f.write(f"Overlap        : {len(overlap)}\n")
        f.write(f"HTML only      : {len(html_only)}\n")
        f.write(f"JSON only      : {len(json_only)}\n\n")

        f.write("=== Interpretation ===\n")
        f.write("- HTML 是初始頁面殼；bs4 不執行 JS，所以職缺卡片可能缺漏/不完整。\n")
        f.write("- JSON list API 是前端渲染清單的資料來源，欄位更完整、分頁也更可控。\n\n")

        f.write("=== JSON-only sample (first 10) ===\n")
        for i, jid in enumerate(list(json_only)[:10], 1):
            j = json_jobs[jid]
            f.write(f"{i}. {j.get('jobName')} / {j.get('custName')} / {j.get('salaryDesc')} / {j.get('jobAddr')}\n")

    print("[DONE] html_jobs.csv / json_jobs.csv / diff_report.txt")


if __name__ == "__main__":
    main()




