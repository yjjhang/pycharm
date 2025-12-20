from bs4 import BeautifulSoup
from datetime import date
import csv


# ✅ 新增：專門讀取本機 HTML 檔案 --------------------------------------

def read_html_file(path: str, encoding: str = "utf-8") -> str:
    """
    【功能】讀取本機 HTML 檔案，回傳 HTML 字串。

    參數:
        path (str): HTML 檔案路徑（相對 / 絕對路徑皆可）
        encoding (str): 檔案編碼，預設 utf-8（若遇亂碼可改 utf-8-sig / big5）

    回傳:
        str: HTML 原始字串內容
    """
    with open(path, "r", encoding=encoding) as f:
        return f.read()


# 1. 解析掛牌時間 + 存 HTML -------------------------------------------

def parse_time(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    span = soup.find(string=lambda t: t and "牌價最新掛牌時間" in t)
    # span 會是像「牌價最新掛牌時間：2025/12/20 09:25」
    if not span:
        return ""
    return span.split("：", 1)[-1].strip()


def save_html_with_time(html: str) -> str:
    time_text = parse_time(html)          # e.g. "2025/12/20 09:25"
    safe_time = (time_text
                 .replace("/", "")
                 .replace(":", "")
                 .replace(" ", "_"))      # 20251220_0925
    filename = f"台銀匯率網_{safe_time}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    return filename


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

    today_str = date.today().strftime("%Y%m%d")
    csv_name = f"{today_str}_匯率試算表.csv"

    with open(csv_name, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["幣別", "現金買入", "現金賣出", "即期買入"])
        writer.writerows(rows)

    return csv_name


# 4. 主程式：改成「讀取本機 HTML」 -------------------------------------

if __name__ == "__main__":
    # ✅ 你本機已存好的 HTML 檔名（自行改成你的檔案）
    html = read_html_file("台銀匯率網的網頁.html", encoding="utf-8")

    fname_html = save_html_with_time(html)
    print("已存 HTML 檔：", fname_html)

    fname_csv = save_rates_csv(html)
    print("已存 CSV 檔：", fname_csv)
