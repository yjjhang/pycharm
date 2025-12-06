import urllib.request
from bs4 import BeautifulSoup

url='https://rate.bot.com.tw/xrt'
# 抓取台銀匯率網的網頁存成html
with urllib.request.urlopen(url) as response:
    html = response.read().decode('utf-8')

# 開啟並讀取 ex08.html 的內容
with open("台銀匯率網的網頁.html", "w", encoding="utf-8") as f:
    f.write(html)

with open("台銀匯率網的網頁.html", "r", encoding="utf-8") as r:
    rate_html=r.read()
# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(rate_html, "html.parser")

# 找出所有 class 有 text-red 的 p 元素
elements = soup.find_all("td", attrs= {"data-table":"本行現金買入"})


# 印出文字內容
for el in elements:
    print(el.get_text())
