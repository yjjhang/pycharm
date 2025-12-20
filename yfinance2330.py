import yfinance as yf
import pandas as pd
from datetime import datetime

TICKERS = {
    "台積電": "2330.TW",
    "台達電": "2308.TW",
    "聯發科": "2454.TW",
}

START_DATE = "2010-01-01"
INTERVAL = "1d"

def download_one(company: str, ticker: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        start=START_DATE,
        interval=INTERVAL,
        auto_adjust=False,     # ✅ 明確指定，FutureWarning 消失
        progress=False
    )

    if df is None or df.empty:
        return pd.DataFrame()

    # ✅ 如果是 MultiIndex 欄位，去掉 ticker 那層，避免 concat 後一堆 NaN
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.reset_index()  # Date 變成欄位
    df.insert(0, "Company", company)
    df.insert(1, "Ticker", ticker)

    # 你想要的欄位順序（可自行增減）
    keep_cols = ["Company", "Ticker", "Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    df = df[keep_cols]

    return df

def main():
    all_data = []
    for company, ticker in TICKERS.items():
        try:
            df = download_one(company, ticker)
            if df.empty:
                print(f"[WARN] {company} ({ticker}) 沒抓到資料")
                continue
            all_data.append(df)
            print(f"[OK] {company} ({ticker}) 筆數：{len(df)}")
        except Exception as e:
            print(f"[ERROR] {company} ({ticker}) 下載失敗：{e}")

    if not all_data:
        raise RuntimeError("三檔都沒有抓到資料，請確認網路或 yfinance 是否可用。")

    merged = pd.concat(all_data, ignore_index=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_股市交易.csv"
    merged.to_csv(filename, index=False, encoding="utf-8-sig")

    print(f"\n已輸出：{filename}")
    print(merged.head())

if __name__ == "__main__":
    main()
