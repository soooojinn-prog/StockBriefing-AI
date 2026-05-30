from __future__ import annotations

import html
import re

import httpx

from stockbriefing.models import NewsItem

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


class NaverNewsClient:
    def __init__(self, client_id: str, client_secret: str, timeout: float = 20.0):
        self._headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        self._timeout = timeout

    def search(self, keyword: str, stock_code: str = "", display: int = 5) -> list[NewsItem]:
        params = {"query": keyword, "display": str(display), "sort": "date"}
        resp = httpx.get(
            NAVER_NEWS_URL, params=params, headers=self._headers, timeout=self._timeout
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            NewsItem(
                title=strip_tags(it.get("title", "")),
                link=it.get("link", ""),
                description=strip_tags(it.get("description", "")),
                pub_date=it.get("pubDate", ""),
                stock_code=stock_code,
                corp_name=keyword,
            )
            for it in items
        ]
