import requests
from bs4 import BeautifulSoup

URL = "https://rate.bot.com.tw/xrt?Lang=zh-TW"

resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

print("幣別\t現金匯率-本行買入")
for row in soup.select('table[title="牌告匯率"] tbody tr'):
    tds = row.find_all("td")
    if len(tds) < 2:
        continue

    currency_div = tds[0].find("div", class_="visible-phone")
    if not currency_div:
        continue
    currency = currency_div.get_text(strip=True)
    cash_buy = tds[1].get_text(strip=True)

    print(f"{currency}\t{cash_buy}")
