# 張詠鈞的python工作區
# File: 企業專題
# Created: 2025/12/13 下午 01:05
import requests
import pandas as pd
from io import StringIO

START_YYYYMM = "202411"
END_YYYYMM   = "202511"

RAW_CSV_FILE  = "ai_chatbot_market_share_monthly_raw.csv"
TIDY_CSV_FILE = "ai_chatbot_market_share_monthly_tidy.csv"

def build_statcounter_ai_chatbot_url(start_yyyymm, end_yyyymm):
    return (
        "https://gs.statcounter.com/ai-chatbot-market-share/"
        "chart.php?bar=1&csv=1"
        "&device=Desktop+%26+Mobile+%26+Tablet+%26+Console"
        "&device_hidden=desktop%2Bmobile%2Btablet%2Bconsole"
        "&multi-device=true"
        f"&fromInt={start_yyyymm}&fromMonthYear={start_yyyymm[:4]}-{start_yyyymm[4:]}"
        "&granularity=monthly"
        "&region=Worldwide&region_hidden=ww"
        "&statType=AI+Chatbot&statType_hidden=ai_chatbot"
        f"&toInt={end_yyyymm}&toMonthYear={end_yyyymm[:4]}-{end_yyyymm[4:]}"
    )

def fetch_csv(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def parse_month_labels(labels):
    """
    將各種可能的月份字串轉成固定 'YYYY-MM'
    全程只用「指定 format」的 to_datetime，避免 Could not infer format 的 warning。
    """
    s = pd.Series(labels, dtype="string").fillna("").str.strip()

    dt = pd.Series(pd.NaT, index=s.index)

    # 依序嘗試常見格式（都指定 format，不走 dateutil）
    fmts = ["%Y-%m", "%Y/%m", "%b %Y", "%B %Y", "%Y-%m-%d", "%Y/%m/%d"]
    for fmt in fmts:
        mask = dt.isna() & s.ne("")
        if not mask.any():
            break
        parsed = pd.to_datetime(s[mask], format=fmt, errors="coerce")
        dt.loc[mask] = parsed

    month = dt.dt.strftime("%Y-%m")

    if month.isna().any():
        bad = s[month.isna()].head(8).tolist()
        raise ValueError(f"Month parse failed. Example values: {bad}")

    return month

def is_monthish(series):
    """
    判斷某欄位的值看起來像不像月份（用於自動判斷 CSV 方向）
    """
    s = series.astype(str).str.strip().head(20)
    if len(s) == 0:
        return False
    pat1 = s.str.match(r"^\d{4}[-/]\d{1,2}$").mean()
    pat2 = s.str.match(r"^[A-Za-z]{3,9}\s+\d{4}$").mean()  # Nov 2024 / November 2024
    pat3 = s.str.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$").mean()
    return (pat1 + pat2 + pat3) >= 0.6

def to_tidy_timeseries(csv_text):
    df = pd.read_csv(StringIO(csv_text))
    first_col = df.columns[0]

    # 情況 A：第一欄是月份、其餘欄是平台（你原本的假設）
    # 情況 B：第一欄是平台、其餘欄是月份（你這次遇到的狀況）
    if is_monthish(df[first_col]):
        # A：月份在列
        tidy = df.melt(id_vars=[first_col], var_name="platform_name", value_name="share")
        tidy["month"] = parse_month_labels(tidy[first_col])
        tidy = tidy.drop(columns=[first_col])
    else:
        # B：平台在列、月份在欄名
        tidy = df.melt(id_vars=[first_col], var_name="month_raw", value_name="share")
        tidy = tidy.rename(columns={first_col: "platform_name"})
        tidy["month"] = parse_month_labels(tidy["month_raw"])
        tidy = tidy.drop(columns=["month_raw"])

    tidy["share"] = pd.to_numeric(tidy["share"], errors="coerce")
    tidy = tidy.dropna(subset=["month", "platform_name", "share"])
    tidy = tidy.sort_values(["month", "platform_name"]).reset_index(drop=True)

    return tidy

def main():
    url = build_statcounter_ai_chatbot_url(START_YYYYMM, END_YYYYMM)
    csv_text = fetch_csv(url)

    # 存 raw（保留證據鏈）
    with open(RAW_CSV_FILE, "w", encoding="utf-8-sig") as f:
        f.write(csv_text)

    tidy = to_tidy_timeseries(csv_text)
    tidy.to_csv(TIDY_CSV_FILE, index=False, encoding="utf-8-sig")

    print("Saved:", TIDY_CSV_FILE)
    print(tidy.head(10))

if __name__ == "__main__":
    main()

