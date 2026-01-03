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

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


# ✅ 用「帶 area 的地區頁」當 seed，比沒有帶 area 的 /jobs/main/category/ 穩
AREA_SEED_URL = "https://www.104.com.tw/jobs/main/category/?area=6001001000&jobsource=category"

CACHE_FILE = os.path.join(os.path.dirname(__file__), "area_cache_104.json")
CACHE_MAX_AGE_SECONDS = 30 * 24 * 3600  # 30 天更新一次即可（縣市代碼非常穩）


# ✅ 內建台灣縣市（備援 + 也可直接用，不靠線上抓）
DEFAULT_TW_AREA_MAP: Dict[str, str] = {
    "基隆市": "6001004000",
    "台北市": "6001001000",
    "新北市": "6001002000",
    "宜蘭縣": "6001003000",
    "桃園市": "6001005000",
    "新竹縣市": "6001006000",
    "苗栗縣": "6001007000",
    "台中市": "6001008000",
    "南投縣": "6001011000",
    "彰化縣": "6001010000",
    "雲林縣": "6001012000",
    "嘉義縣市": "6001013000",
    "台南市": "6001014000",
    "高雄市": "6001016000",
    "屏東縣": "6001018000",
    "台東縣": "6001019000",
    "花蓮縣": "6001020000",
    "澎湖縣": "6001021000",
    "金門縣": "6001022000",
    "連江縣": "6001023000",
}


@dataclass
class AreaResolveResult:
    input_text: str
    normalized: str
    matched_name: str
    area_code: str


def _normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("臺", "台")
    s = re.sub(r"\s+", "", s)
    return s


def _load_cache() -> Optional[Dict[str, str]]:
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
        ts = obj.get("_fetched_at", 0)
        if not isinstance(ts, (int, float)):
            return None
        if time.time() - ts > CACHE_MAX_AGE_SECONDS:
            return None
        mapping = obj.get("mapping", {})
        if isinstance(mapping, dict) and mapping:
            return mapping
        return None
    except Exception:
        return None


def _save_cache(mapping: Dict[str, str]) -> None:
    obj = {
        "_fetched_at": int(time.time()),
        "mapping": mapping,
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def fetch_area_mapping(timeout: int = 20) -> Dict[str, str]:
    """
    從 104 地區找工作頁（帶 area 的 seed）抓縣市 -> area code
    回傳：{"台北市": "6001001000", ...}
    """
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    r = requests.get(AREA_SEED_URL, headers=headers, timeout=timeout)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")

    mapping: Dict[str, str] = {}

    # 解析所有 href 含 area= 的連結
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "area=" not in href:
            continue

        m = re.search(r"[?&]area=([0-9,]+)", href)
        if not m:
            continue

        area_code = m.group(1).strip()
        name = _normalize_text(a.get_text())
        if not name:
            continue

        # 把像「台北市 119329」這種文字切掉數字，只保留縣市名
        name = re.sub(r"\d+$", "", name).strip()

        # 只收「台灣縣市」常見格式（避免海外/大陸區塊污染）
        if name in DEFAULT_TW_AREA_MAP or name.endswith(("市", "縣", "縣市")):
            mapping.setdefault(name, area_code)

    # 如果抓到的少，回傳空 dict，讓上層走 fallback
    if len(mapping) < 10:
        return {}

    return mapping


def get_area_mapping(force_refresh: bool = False) -> Dict[str, str]:
    """
    回傳最終 mapping：
    - 先嘗試 cache
    - 再嘗試線上抓取
    - 最後 fallback 內建 DEFAULT_TW_AREA_MAP
    """
    if not force_refresh:
        cached = _load_cache()
        if cached:
            # 合併內建（以 cached 為優先）
            merged = dict(DEFAULT_TW_AREA_MAP)
            merged.update(cached)
            return merged

    try:
        online = fetch_area_mapping()
        if online:
            _save_cache(online)
            merged = dict(DEFAULT_TW_AREA_MAP)
            merged.update(online)
            return merged
    except Exception:
        pass

    # fallback
    return dict(DEFAULT_TW_AREA_MAP)


def list_supported_areas() -> List[str]:
    mapping = get_area_mapping()
    return sorted(mapping.keys())


def resolve_area(user_input: str, force_refresh: bool = False) -> AreaResolveResult:
    raw = user_input or ""
    s = _normalize_text(raw)
    if not s:
        raise ValueError("地區不可為空。")

    mapping = get_area_mapping(force_refresh=force_refresh)

    # 常見別名
    alias = {
        "新竹": "新竹縣市",
        "嘉義": "嘉義縣市",
    }
    if s in alias:
        target = alias[s]
        code = mapping.get(target)
        if not code:
            raise ValueError(f"地區「{raw}」對應到「{target}」但未找到代碼。")
        return AreaResolveResult(raw, s, target, code)

    # 直接命中
    if s in mapping:
        return AreaResolveResult(raw, s, s, mapping[s])

    # 省略市/縣：台北 -> 台北市
    candidates: List[Tuple[str, str]] = []
    for suffix in ("市", "縣", "縣市"):
        name = s + suffix
        if name in mapping:
            candidates.append((name, mapping[name]))

    if len(candidates) == 1:
        name, code = candidates[0]
        return AreaResolveResult(raw, s, name, code)

    # 模糊包含：輸入「桃園」匹配到「桃園市」
    fuzzy = [(k, v) for k, v in mapping.items() if s in k]
    if len(fuzzy) == 1:
        name, code = fuzzy[0]
        return AreaResolveResult(raw, s, name, code)

    if len(fuzzy) > 1:
        options = "、".join(k for k, _ in fuzzy[:10])
        raise ValueError(f"地區「{raw}」匹配到多個可能：{options}（請輸入更完整名稱）")

    raise ValueError(f"找不到地區「{raw}」。可用縣市例如：{', '.join(list_supported_areas()[:10])} ...")


