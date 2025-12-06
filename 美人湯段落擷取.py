from bs4 import BeautifulSoup

# 讀取 HTML 檔案
with open("紅色段落文字.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")#用html解析內容

#定義一個檢查紅色段落的函式
def is_red_paragraph(tag):
    # 只處理 <p> 標籤
    if tag.name != "p":
        return False

    # 1. 先檢查 class 名稱是否包含 red-text（依你前面範例）
    classes = tag.get("class", [])
    if "red-text" in classes:
        return True

    # 2. 再檢查 style 裡面是否有 color: red（大小寫與空白都略過）
    style = (tag.get("style") or "").lower()
    # 簡單判斷：style 字串裡有 "color" 且有 "red"
    if "color" in style and "red" in style:
        return True

    return False

# 找出所有「紅色」的段落
red_paragraphs = [p for p in soup.find_all(is_red_paragraph)]

# 印出結果
for i, p in enumerate(red_paragraphs, start=1):
    print(f"第 {i} 個紅色段落：")
    print(p.get_text(strip=True))
    print("-" * 30)
