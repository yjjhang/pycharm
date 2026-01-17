import requests
from bs4 import BeautifulSoup
from datetime import datetime
import csv
from pathlib import Path
from Sort_Dir import sort_existing_files
from Sort_Dir import HTML_DIR
from save_sqlite_tb import save_cash_and_spot_buy_to_sqlite
# ✅ 新增：專門讀取本機 HTML 檔案 --------------------------------------

TB_URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"

def fetch_tb_html(timeout: int = 20) -> str:
    """下載台銀匯率網最新 HTML，回傳 HTML 字串"""
    r = requests.get(TB_URL, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def read_html_file(path: str, encoding: str = "utf-8") -> str:
    path = Path(path)
    with path.open("r", encoding=encoding) as f:
        return f.read()


# 1. 解析掛牌時間 + 存 HTML -------------------------------------------

def parse_time(html: str) -> str:
    # 你 DevTools 截圖顯示時間在 <span class="time">2026/01/10 09:25</span>
    soup = BeautifulSoup(html, "html.parser")
    time_span = soup.select_one("p.text-info span.time") or soup.select_one("span.time")
    return time_span.get_text(strip=True) if time_span else ""


def save_html_with_time(html: str) -> str:
    """
    依你的需求：存成 YYYYMMDD_台銀匯率網.html
    - 日期優先用掛牌時間的日期（更準）
    - 取不到就用本機日期備援
    """
    time_text = parse_time(html)  # e.g. "2026/01/10 09:25"
    if time_text:
        yyyymmdd = time_text.split()[0].replace("/", "")  # 20260110
    else:
        yyyymmdd = datetime.now().strftime("%Y%m%d")

    filename = f"{yyyymmdd}_台銀匯率網.html"

    # ✅ 建議：直接存到你的 HTML_DIR（不要落在 cwd 才讓 Sort_Dir 搬）
    out_path = HTML_DIR / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    return str(out_path)


# 2. 解析：幣別 + 現金買入 / 現金賣出 / 即期買入 -----------------------

def get_cash_rates(html: str):
    """
    回傳 list[ (幣別, 現金買入, 現金賣出) ]
    """
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table")
    rows = table.tbody.find_all("tr")

    data = []
    for tr in rows:
        td_cur  = tr.find("td", attrs={"data-table": "幣別"})
        td_buy  = tr.find("td", attrs={"data-table": "本行現金買入"})
        td_sell = tr.find("td", attrs={"data-table": "本行現金賣出"})
        if not (td_cur and td_buy and td_sell):
            continue

        cur_div = td_cur.find("div", class_="hidden-phone print_show xrt-cur-indent")
        if cur_div:
            cur = cur_div.get_text(strip=True)
        else:
            cur = td_cur.get_text(strip=True)

        cash_buy  = td_buy.get_text(strip=True)
        cash_sell = td_sell.get_text(strip=True)

        data.append((cur, cash_buy, cash_sell))

    return data


def get_cash_and_spot_buy(html: str):
    """
    回傳 list[ (幣別, 現金買入, 即期買入) ]
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    rows = table.tbody.find_all("tr")

    result = []
    for tr in rows:
        td_cur      = tr.find("td", attrs={"data-table": "幣別"})
        td_cash_buy = tr.find("td", attrs={"data-table": "本行現金買入"})
        td_spot_buy = tr.find("td", attrs={"data-table": "本行即期買入"})
        if not (td_cur and td_cash_buy and td_spot_buy):
            continue

        cur_div = td_cur.find("div", class_="hidden-phone print_show xrt-cur-indent")
        if cur_div:
            currency = cur_div.get_text(strip=True)
        else:
            currency = td_cur.get_text(strip=True)

        cash_buy = td_cash_buy.get_text(strip=True)
        spot_buy = td_spot_buy.get_text(strip=True)

        result.append((currency, cash_buy, spot_buy))

    return result


# 3. 只選我們要的欄位，寫成「系統日期_匯率試算表.csv」 ----------------

def save_rates_csv(html: str) -> str:
    """
    只輸出 4 欄：
      幣別, 現金買入, 現金賣出, 即期買入
    """
    all_rates  = get_cash_rates(html)          # (cur, cash_buy, cash_sell)
    spot_rates = get_cash_and_spot_buy(html)   # (cur, cash_buy, spot_buy)

    spot_map = {cur: spot_buy for (cur, cash_buy, spot_buy) in spot_rates}

    rows = []
    for cur, cash_buy, cash_sell in all_rates:
        spot_buy = spot_map.get(cur, "")
        rows.append([cur, cash_buy, cash_sell, spot_buy])

    today_str = datetime.today().strftime("%Y%m%d")
    csv_name = f"{today_str}_台銀匯率試算表.csv"

    with open(csv_name, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["幣別", "現金買入", "現金賣出", "即期買入"])
        writer.writerows(rows)

    return csv_name


# 4. 主程式：改成「讀取本機 HTML」 -------------------------------------

if __name__ == "__main__":
    # ✅ 你本機已存好的 HTML 檔名（自行改成你的檔案）
    html = read_html_file(HTML_DIR / "台銀匯率網的網頁.html", encoding="utf-8")

    fname_html = save_html_with_time(html)
    print("已存 HTML 檔：", fname_html)

    fname_csv = save_rates_csv(html)
    print("已存 CSV 檔：", fname_csv)

    rows = get_cash_and_spot_buy(html)
    db_path = str((HTML_DIR.parent / "tb_rates.sqlite"))
    save_cash_and_spot_buy_to_sqlite(db_path, rows)
    print(f"[OK] SQLite 已更新：{db_path} | 筆數：{len(rows)}")

    moved = sort_existing_files(Path.cwd())
    print(f"[OK] Sort_Dir 歸檔完成，本次移動檔案數：{moved}")

