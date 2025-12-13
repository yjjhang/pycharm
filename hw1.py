import requests
from bs4 import BeautifulSoup
import json
import re

url = "https://kma.kkbox.com/charts/weekly/newrelease?terr=tw&lang=tc"

resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

# 抓所有 <script>，通常倒數第二個裡面會有 var chart = [...]
scripts = soup.select("script")
js_text = scripts[-2].string  # 保險一點可以先 print 看是哪一個

# 用正則把 var chart = [...] 抓出來
m = re.search(r"var\s+chart\s*=\s*(\[{.*}\]);", js_text)
chart_json = m.group(1)

songs = json.loads(chart_json)

print("名次\t歌手\t歌名")
for song in songs[:10]:  # 只取前 10 名
    rank = song["rankings"]["this_period"]
    artist = song["artist_name"]
    title = song["song_name"]
    print(f"{rank}\t{artist}\t{title}")
