# 張詠鈞的python工作區
# File: 企業專題
# Created: 2025/12/13 下午 01:05
import pandas

import ex11擔任需求分析與AI討論_模組 as m


def print_html_file(path, encoding="utf-8"):
    """
    【功能】讀取本機 HTML 檔案並回傳整份 HTML 字串。

    用途：
        - 把已下載/已儲存的 HTML 檔讀進來，提供給 BeautifulSoup 做解析。
        - 適合離線解析，不需要 requests 連線。

    參數：
        path (str):
            HTML 檔案路徑（可用相對路徑或絕對路徑）
            例： "台銀匯率網的網頁.html"
            或： r"C:\\temp\\台銀匯率網的網頁.html"
        encoding (str):
            檔案編碼，預設 "utf-8"
            若遇到亂碼可嘗試 "big5" 或 "utf-8-sig"

    回傳：
        str:
            讀取到的 HTML 原始字串內容
    """
    # 以文字模式開啟檔案並用指定編碼解碼
    with open(path, "r", encoding=encoding) as f:
        # 一次讀取整份檔案內容成為字串
        html = f.read()

    # 回傳 HTML 字串，交給後續 bs4 解析
    return html


def parse_rate(elements):
    """
    【功能】將匯率文字轉成 float 清單回傳。
    規則：若文字為 '-' 或空字串，視為沒有匯率 → 0.0

    參數:
        elements (list[bs4.element.Tag]): m.bs4_soup(html) 回傳的 Tag 清單

    回傳:
        list[float]: 轉型後的匯率數值清單
    """
    values = []
    for e in elements:
        text = e.get_text(strip=True)

        if text == "-" or text == "":
            values.append(0.0)
        else:
            values.append(float(text))

    return values
def parse_coin(elements):
    """
    【功能】將幣別文字轉成 str 清單回傳。
    規則：若文字為空字串，回傳 "UNKNOWN"（避免空值）

    參數:
        elements (list[bs4.element.Tag]): m.bs4_coin(html) 回傳的 Tag 清單

    回傳:
        list[str]: 幣別文字清單（例如：['美金 (USD)', '港幣 (HKD)', ...]）
    """
    coins = []
    for e in elements:
        text = e.get_text(strip=True)

        if text == "":
            coins.append("UNKNOWN")
        else:
            coins.append(text)

    return coins


def main():
    """
    【功能】主流程入口：串接「讀檔 → 模組解析 → 輸出」。

    流程：
        1) 使用 print_html_file() 讀取本機 HTML 檔，取得 html 字串
        2) 呼叫「模組」m.bs4_soup(html) 解析 html，取得目標元素清單
        3) 使用 parse_bs4(elements) 把解析結果逐筆輸出到 console

    注意：
        - 這裡刻意把「解析」放在模組 ex11擔任需求分析與AI討論_模組.py
          主程式只負責流程控制與輸出，方便未來擴充與維護。

    回傳：
        None
    """
    html = print_html_file("台銀匯率網的網頁.html")

    coin_elements = m.bs4_coin(html)  # ✅ 呼叫模組抓幣別
    coins = m.parse_coin(coin_elements)  # ✅ 轉成文字清單

    print("幣別數量:", len(coins))
    for c in coins:
        print(c)

# Python 慣用寫法：只有直接執行此檔案時才跑 main()
# 如果此檔案被別的程式 import，就不會自動執行 main()
if __name__ == "__main__":
    main()
