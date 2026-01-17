# 張詠鈞的python工作區
# File: test_104url
# Created: 2026/1/10 下午 12:28


import requests

JSON_REQUEST_URL = "https://www.104.com.tw/jobs/search/?area=6001005000&jobsource=joblist_search&keyword=Python%E5%B7%A5%E7%A8%8B%E5%B8%AB&mode=s&page=1&order=15&jobcat=2007001004"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.104.com.tw/jobs/search/",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
}

r = requests.get(JSON_REQUEST_URL, headers=headers, timeout=20, allow_redirects=True)

print("HTTP:", r.status_code)
print("Final URL:", r.url)
print("Content-Type:", r.headers.get("Content-Type"))
print("Length:", len(r.text))
print("First 200 chars:\n", r.text[:200])