# pre_webcrawler.py
import requests
from bs4 import BeautifulSoup


class PageProbe(object):
    """網頁探測工具：
    - 檢查狀態碼
    - （選擇性）檢查 HTML 內是否包含某段文字
    """

    def __init__(self, user_agent=None, timeout=10):
        if user_agent is None:
            user_agent = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.timeout = timeout

    def quick_probe(self, url, keyword=None):
        """回傳一個 dict 說明這個網址的基本狀況。

        keyword 不為 None 時，會順便檢查 HTML 裡有沒有這段文字。
        """
        result = {
            "url": url,
            "ok": False,
            "status_code": None,
            "keyword": keyword,
            "keyword_found": None,
            "error": None,
        }

        try:
            resp = self.session.get(url, timeout=self.timeout)
        except requests.RequestException as e:
            result["error"] = str(e)
            return result

        result["status_code"] = resp.status_code

        if not resp.ok:
            # 不是 2xx，直接回傳
            result["ok"] = False
            return result

        # 狀態碼 OK
        result["ok"] = True

        if keyword:
            soup = BeautifulSoup(resp.text, "html.parser")
            found = soup.find(string=lambda s: s and keyword in s)
            result["keyword_found"] = bool(found)

        return result
