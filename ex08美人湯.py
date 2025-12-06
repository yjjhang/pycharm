from bs4 import BeautifulSoup

# 開啟並讀取 ex08.html 的內容
with open("台銀匯率網的網頁.html", "r", encoding="utf-8") as f:
    html = f.read()

# 使用 BeautifulSoup 解析 HTML
soup = BeautifulSoup(html, "html.parser")

# 找出所有 class 有 text-red 的 p 元素
elements = soup.find_all("td", class_="rate-content-cash")
# 印出文字內容
for el in elements:
    print(el.get_text())
print('-------------------------------------------------------------------')
#接下來抓取幣別位置
elements=soup.find_all("div", class_="print_show")
for el in elements:
    print('===============================================================')#想知道裡面的內容包含了什麼，開頭第一段丟進去
    #發現其實抓取了很多空白的字串內容
    x=el.get_text()
    print(type(x))#確認x的html抓取的內容為Str
    print(x.strip())#Str就可以使用去除空白字串的方法取得乾淨內容
