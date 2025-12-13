import csv
import urllib.request
from bs4 import BeautifulSoup
from numpy.ma.core import append

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
elements = soup.find_all("td", class_="rate-content-cash")

print("---------------------------------------------------------------------------------")
for el in elements:
    print(el.get_text())
#收集現金匯率資料
#可利用列表生成式把資料存在列表中
list_rate=[el.get_text() for el in elements]
print(list_rate)
#把列表的'-'替換成零
for i in range (len(list_rate)):
    if list_rate[i]== '-':
        list_rate[i] ='0'
print(list_rate)

#找出幣別的資料
elements_1 = soup.find_all("div", class_="print_show")
for el in elements_1:
    print('===============================================================')#想知道裡面的內容包含了什麼，開頭第一段丟進去
    #發現其實抓取了很多空白的字串內容
    x=el.get_text()
    print(type(x))#確認x的html抓取的內容為Str
    print(x.strip())#Str就可以使用去除空白字串的方法取得乾淨內容
#印出幣別的資料，並清除掉干擾的空格字元

# 印出文字內容

#把列表中的字串轉換成浮點數float
money=[float(x) for x in list_rate]
print(money)
#現在就可以把匯率的金額跟幣別結合起來
coin=[el.get_text().strip() for el in elements_1]
print(coin)
row_rate=[]
row_rate.append(["幣別", "買入金額", "賣出金額"])
#把幣別結合成 "幣別"、"買入金額"、"賣出金額"金額後存成CSV檔案
for j,k in enumerate(coin):
    buy=money[j*2]
    sell=money[j*2+1]
    row_rate.append([k,buy,sell])


save_csv='台銀匯率_20251212.csv'
with open(save_csv,'w', encoding="utf-8", newline='') as w:
    writer=csv.writer(w)
    writer.writerows(row_rate)
print("台銀外匯檔案輸出完成")



