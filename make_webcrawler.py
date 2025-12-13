import csv
import json
import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from pre_webcrawler import PageProbe

probe = PageProbe()

url = "https://epic7.onstove.com/zh-TW/gg/herorecord"

info = probe.quick_probe(url, keyword="勝率")

print(info)


HERO_LIST_JSON = "https://static.smilegatemegaport.com/gameRecord/epic7/epic7_hero.json"
HERO_RECORD_URL_ZHTW = "https://epic7.onstove.com/zh-TW/gg/herorecord/{code}"  # {code} e.g. c1129
OUT_CSV = "epic7_hero_record_zhTW.csv"

# 友善爬取：別太快，避免被擋
REQUEST_SLEEP_SEC = 0.35
TIMEOUT = 20


def safe_float(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    s = s.strip().replace("%", "")
    try:
        return float(s)
    except ValueError:
        return None


def extract_first(patterns: List[str], text: str, flags=0) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1)
    return None


def parse_hero_codes(hero_json: object) -> List[str]:
    """
    盡量兼容不同 JSON 結構：
    - dict: { "c1001": {...}, "c1002": {...} }
    - list: [ {"code": "c1001", ...}, ... ]
    """
    codes = set()

    def add_code(x: str):
        if isinstance(x, str) and re.fullmatch(r"c\d{3,5}", x):
            codes.add(x)

    if isinstance(hero_json, dict):
        for k, v in hero_json.items():
            add_code(k)
            # 有些結構會把 code 放在內層
            if isinstance(v, dict):
                for key in ("code", "heroCode", "hero_code", "id"):
                    if key in v:
                        add_code(str(v[key]))
    elif isinstance(hero_json, list):
        for item in hero_json:
            if isinstance(item, dict):
                for key in ("code", "heroCode", "hero_code", "id"):
                    if key in item:
                        add_code(str(item[key]))

    return sorted(codes)


def fetch_json(session: requests.Session, url: str) -> object:
    r = session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_html(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def parse_hero_record_page(html: str, url: str, code: str) -> Dict:
    """
    因為頁面可能改版，採用「從整頁文字抓關鍵字附近的數字」策略。
    你之後要加欄位也很容易。
    """
    soup = BeautifulSoup(html, "lxml")
    title = (soup.title.text or "").strip() if soup.title else ""

    # 把頁面所有文字壓成一段，方便 regex
    text = soup.get_text(" ", strip=True)

    # 常見欄位 (中英都兼容)
    win_rate = safe_float(extract_first([
        r"勝率\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Win\s*Rate\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    ], text, flags=re.IGNORECASE))

    pick_rate = safe_float(extract_first([
        r"PICK機率\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Pick\s*Rate\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    ], text, flags=re.IGNORECASE))

    ban_rate = safe_float(extract_first([
        r"BAN機率\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Ban\s*Rate\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    ], text, flags=re.IGNORECASE))

    # 例： “勝率. 183 名/ 36538.11%.” → rank=183, total=36538
    rank = extract_first([
        r"勝率[^0-9]*([0-9]+)\s*名\s*/",
        r"Win\s*Rate[^0-9]*([0-9]+)\s*/",
    ], text, flags=re.IGNORECASE)
    total = extract_first([
        r"名\s*/\s*([0-9]+)",
        r"Ranking:\s*[0-9]+\s*/\s*([0-9]+)",
    ], text, flags=re.IGNORECASE)

    # 嘗試抓「最近更新」字樣（例如：最近更新: 1 天前）
    last_updated = extract_first([
        r"最近更新[:：]\s*([^\s]+)",
        r"Last\s*Updated[:：]\s*([^\s]+)",
    ], text, flags=re.IGNORECASE)

    # 嘗試從 title 拆英雄名（通常像： “艾莉雅 - 第七史詩查詢戰績”）
    hero_name = None
    if title:
        hero_name = title.split("-")[0].strip()

    return {
        "code": code,
        "hero_name": hero_name,
        "url": url,
        "last_updated": last_updated,
        "rank": int(rank) if rank and rank.isdigit() else None,
        "total_rank_pool": int(total) if total and total.isdigit() else None,
        "pick_rate_pct": pick_rate,
        "win_rate_pct": win_rate,
        "ban_rate_pct": ban_rate,
    }


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; Epic7HeroCrawler/1.0; +https://example.com)"
    })

    hero_json = fetch_json(session, HERO_LIST_JSON)
    codes = parse_hero_codes(hero_json)
    if not codes:
        raise RuntimeError("抓不到英雄代碼清單（epic7_hero.json 結構可能變了）")

    rows = []
    for i, code in enumerate(codes, 1):
        url = HERO_RECORD_URL_ZHTW.format(code=code)
        try:
            html = fetch_html(session, url)
            row = parse_hero_record_page(html, url, code)
            rows.append(row)
            print(f"[{i}/{len(codes)}] OK {code} {row.get('hero_name') or ''}")
        except Exception as e:
            print(f"[{i}/{len(codes)}] FAIL {code} -> {e}")
        time.sleep(REQUEST_SLEEP_SEC)

    # 輸出 CSV
    fieldnames = [
        "code", "hero_name", "url", "last_updated",
        "rank", "total_rank_pool",
        "pick_rate_pct", "win_rate_pct", "ban_rate_pct"
    ]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nDone -> {OUT_CSV} (rows={len(rows)})")


if __name__ == "__main__":
    main()

