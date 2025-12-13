# 張詠鈞的python工作區
# File: 企業專題
# Created: 2025/12/13 下午 01:05
from bs4 import BeautifulSoup

def bs4_soup(html):
    """
    將 HTML 字串交給 BeautifulSoup 解析，並用條件找出目標元素清單。

    參數:
        html (str): HTML 原始字串內容

    回傳:
        list[bs4.element.Tag]: 符合條件的標籤物件清單（每個元素是一個 <td> tag）
    """
    # 建立 BeautifulSoup 物件（把 HTML 轉成可搜尋/可走訪的 DOM 結構）
    soup = BeautifulSoup(html, "html.parser")

    # 找出所有符合條件的 <td> 標籤
    # class_ 可以用空白分隔多個 class 名稱，BeautifulSoup 會視為「同時包含這些 class」
    elements = soup.find_all("td", class_="rate-content-cash text-right print_hide")

    # 回傳元素清單，交給下一步做文字輸出或資料整理
    return elements

def parse_bs4(elements):
    """
    將 bs4 找到的元素清單轉成 float 清單回傳。
    規則：若文字為 '-' 或空字串，視為沒有匯率，回傳 0.0。
    """
    values = []
    for e in elements:
        text = e.get_text(strip=True)

        if text == "-" or text == "":
            values.append(0.0)
        else:
            values.append(float(text))

    return values

def bs4_coin(html):
    """
    【功能】解析台銀匯率頁面，抓取「幣別欄位」的文字元素(div)清單。

    參數:
        html (str): HTML 原始字串內容

    回傳:
        list[bs4.element.Tag]: 幣別文字所在的 div 標籤清單（如：美金(USD)、港幣(HKD)）
    """
    soup = BeautifulSoup(html, "html.parser")

    # ✅ 抓「幣別那格 td」裡面的 div（依你截圖：div.visible-phone.print_hide）
    return soup.select("td.currency.phone-small-font div.visible-phone.print_hide")

def parse_coin(elements):
    """
    【功能】將幣別 div 清單轉成幣別文字清單並回傳。

    參數:
        elements (list[bs4.element.Tag]): bs4_coin() 回傳的 div 清單

    回傳:
        list[str]: 幣別文字清單（例如：['美金 (USD)', '港幣 (HKD)', ...]）
    """
    coins = []
    for e in elements:
        coins.append(e.get_text(strip=True))
    return coins
