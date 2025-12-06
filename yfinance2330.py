import yfinance as yf

# 台積電在 Yahoo Finance 的代號
TICKER = "2330.TW"

# 抓 2010-01-01 之後的日K交易紀錄，你也可以自己改起始日
data = yf.download(
    TICKER,
    start="2010-01-01",
    interval="1d",
    progress=False
)

# 存成 CSV 檔，Excel 也可以直接開啟
filename = "2330_交易紀錄.csv"
data.to_csv(filename, encoding="utf-8-sig")

print(f"已下載 {TICKER} 交易紀錄並存成：{filename}")
print(data.head())  # 順便印出前幾筆確認
