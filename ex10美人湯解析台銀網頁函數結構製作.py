import urllib.request
from bs4 import BeautifulSoup
import csv

URL = "https://rate.bot.com.tw/xrt"
HTML_FILE = "台銀匯率網的網頁.html"
CSV_FILE = "台銀外匯買入賣出.csv"


def fetch_html(url):
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def save_html(html, filename):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)


def clean_rate_list(rate_list):
    """清洗匯率列表：'-'→0，去空白，轉 float。"""
    cleaned = []
    for s in rate_list:
        s = s.strip()
        if s == '-':
            s = '0'
        cleaned.append(float(s))
    return cleaned


def parse_coins(soup):
    """從 soup 中抓幣別列表"""
    elements = soup.find_all("div", class_="print_show")
    coin_list = [el.get_text().strip() for el in elements]
    return coin_list


def parse_cash_rates(soup):
    """從 soup 中抓現金匯率（買入 + 賣出），回傳已清洗好的 float 列表"""
    elements = soup.find_all("td", class_="rate-content-cash")
    raw_rates = [el.get_text() for el in elements]
    money_list = clean_rate_list(raw_rates)
    return money_list


def build_rows(coin_list, money_list):
    """把幣別 + 金額列表 組成 rows（含標題列）"""
    rows = [["幣別", "買入金額", "賣出金額"]]

    for idx, c in enumerate(coin_list):
        buy = money_list[idx * 2]
        sell = money_list[idx * 2 + 1]

        rows.append([c, buy, sell])

    return rows


def save_to_csv(rows, filename):
    with open(filename, "w", encoding="utf-8-sig", newline="") as w:
        writer = csv.writer(w)
        writer.writerows(rows)


def main():
    # 1. 抓 HTML
    html = fetch_html(URL)

    # 2. 可選：存 HTML 方便 debug
    save_html(html, HTML_FILE)

    # 3. 只在這裡解析一次 soup
    soup = BeautifulSoup(html, "html.parser")

    # 4. 分別解析幣別 & 匯率
    coin_list = parse_coins(soup)
    money_list = parse_cash_rates(soup)

    # 5. 組成表格資料
    rows = build_rows(coin_list, money_list)

    # 6. 存成 CSV
    save_to_csv(rows, CSV_FILE)
    print("台銀外匯檔案輸出完成：", CSV_FILE)


if __name__ == "__main__":
    main()
