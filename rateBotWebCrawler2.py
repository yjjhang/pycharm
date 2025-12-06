import urllib.request

URL = "https://rate.bot.com.tw/xrt/flcsv/0/day"  # 台銀匯率 CSV 連結
FILENAME = "台銀檔案2.csv"                        # 固定檔名

with urllib.request.urlopen(URL) as resp:
    data = resp.read()  # 把檔案內容抓下來（bytes）

with open(FILENAME, "wb") as f:
    f.write(data)

print(f"已下載完成：{FILENAME}")
