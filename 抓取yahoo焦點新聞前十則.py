import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

BASE_URL = "https://tw.news.yahoo.com/"

def fetch_html(url):
    """抓取 Yahoo 新聞首頁 HTML。"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.text

def is_news_url(href: str) -> bool:
    """
    判斷是不是「新聞文章」連結：
    - 網域是 tw.news.yahoo.com
    - 路徑不是 /
    - 路徑以 .html 結尾
    - 路徑裡包含 '-'（通常會有 -數字ID.html）
    """
    if not href:
        return False

    full = urljoin(BASE_URL, href)
    u = urlparse(full)

    if u.netloc != "tw.news.yahoo.com":
        return False

    path = u.path or ""
    if path == "/":
        return False

    if not path.endswith(".html"):
        return False

    if "-" not in path:
        return False

    return True

def get_focus_top10():
    html = fetch_html(BASE_URL)
    soup = BeautifulSoup(html, "html.parser")

    results = []
    seen_urls = set()

    # 先用「整頁的 <a>」掃過去，挑出符合 is_news_url 的前 10 則
    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        href = a["href"]

        if not title:
            continue

        full_url = urljoin(BASE_URL, href)

        if not is_news_url(full_url):
            continue

        if full_url in seen_urls:
            continue

        seen_urls.add(full_url)
        results.append({
            "title": title,
            "url": full_url
        })

        if len(results) >= 10:
            break

    return results

def main():
    top10 = get_focus_top10()

    print("Yahoo 奇摩新聞首頁『焦點新聞』前 10 則（依頁面順序）：\n")
    print(f"實際抓到篇數：{len(top10)}\n")

    for i, news in enumerate(top10, start=1):
        print(f"{i}. {news['title']}")
        print(f"   {news['url']}\n")

if __name__ == "__main__":
    main()
