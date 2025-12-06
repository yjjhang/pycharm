import requests
import datetime

# 這個就是台銀「匯出CSV」按鈕背後的連結
URL = "https://rate.bot.com.tw/xrt/flcsv/0/day"

def main():
    # 1. 直接用 requests 把 CSV 抓下來
    resp = requests.get(URL)
    resp.raise_for_status()  # 如果失敗會丟出錯誤

    # 2. 用日期當檔名
    today = datetime.datetime.now().strftime("%Y%m%d")
    filename = f"bot_rate_{today}.csv"

    # 3. 寫檔
    with open(filename, "wb") as f:
        f.write(resp.content)

    print(f"匯率 CSV 已下載完成：{filename}")


if __name__ == "__main__":
    main()
