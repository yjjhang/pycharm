class 美人湯:
    # 定義一個用來表示「網頁標籤節點」的類別
    def __init__(self, html_tag, html_class, html_text):
        # 設定這個節點的標籤名稱、class 名稱列表，以及文字內容
        self.html_tag = html_tag
        self.html_class = html_class if html_class else []
        self.html_text = html_text

    def show_tag(self):
        # 依序顯示標籤名稱、class 清單與文字內容（各一行）
        print(self.html_tag)
        print(self.html_class)
        print(self.html_text)


class 段落:
    def __init__(self):
        # 建立四個美人湯物件，模擬網頁上的四個 <p> 標籤
        p1 = 美人湯("p", ["text-red", "large-text"], "今天是第一天上課的天氣晴")
        p2 = 美人湯("p", ["text-blue"], "這課程使用的IDE是pycharm")
        p3 = 美人湯("p", ["text-yellow", "text-blue"], "終於開始講物件導向的課程")
        p4 = 美人湯("p", ["text-pink", "large-text"], "我要加強這一個觀念")
        # 用列表把這四個標籤節點存起來，模擬 BeautifulSoup 裡面的樹狀結構
        self.WebCrawler = [p1, p2, p3, p4]

    # 仿照 BeautifulSoup 設計一個簡化版的 find_all() 函數：
    # 根據標籤名稱搜尋，並印出找到的結果
    def find_all(self, name):
        search = []
        for x in self.WebCrawler:
            # ✅ 比的是「標籤名稱」
            if x.html_tag == name:
                x.show_tag()
                search.append(x)

        # ✅ 只有真的沒找到，才顯示訊息
        if not search:
            print("search nothing!")
        return search

    # 設計一個函式，用來判斷：
    #   標籤名稱是否等於 name，且指定的 class_ 是否有出現在該標籤的 class 清單中
    # 若符合條件，就把這些物件收集成列表回傳
    def find_text(self, name, class_):
        # 使用列表生成式，回傳所有同時符合 tag 與 class 條件的美人湯物件
        return [x for x in self.WebCrawler if x.html_tag == name and class_ in x.html_class]


soup = 段落()
print("第一行搜尋結果:")
soup.find_all("p")

print("第二行搜尋結果:")
soup.find_all("a")

找到 = soup.find_text(name="p", class_="text-blue")
print("第三行搜尋結果:")
# 再透過迴圈把 find_text 回傳的物件依序顯示出來，
# 由於美人湯類別本身已有 show_tag() 方法，所以可以直接呼叫
for i in 找到:
    i.show_tag()
    # print(i.html_text)  # 若只想看文字內容，也可以這樣印
