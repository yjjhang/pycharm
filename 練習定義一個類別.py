class 美人湯:
    #定義網頁資料名稱
    def __init__(self, html_tag, html_class, html_text):
        #定自資料名稱的類型
        self.html_tag = html_tag
        self.html_class = html_class if html_class else []
        self.html_text = html_text
    def show_tag(self):
        print(self.html_tag)
        print(self.html_class)
        print(self.html_text)

p1 = 美人湯("p",["text_red"],"今天是第一天上課的天氣晴")
p2 = 美人湯("p",["text_blue"],"這課程使用的IDE是pycharm")
p3 = 美人湯("p",["text_yellow"],"終於開始講物件導向的課程")
p4 = 美人湯("p",["text_pink"],"我要加強這一個觀念")

美人湯=[p1,p2,p3,p4]

for item in 美人湯:
    print("tag:", item.html_tag)
    print("class:", item.html_class)
    print("text:", item.html_text)
    print("----------")

for i  in 美人湯:
    print(i.html_tag, i.html_class, i.html_text)

p2.show_tag()