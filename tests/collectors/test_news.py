import httpx
import respx

from stockbriefing.collectors.news import NaverNewsClient, strip_tags


def test_strip_tags_removes_b_and_entities():
    assert strip_tags("삼성<b>전자</b> &amp; SK") == "삼성전자 & SK"


@respx.mock
def test_search_returns_news_items_with_stock_code():
    payload = {
        "items": [
            {
                "title": "삼성<b>전자</b> 신규 계약",
                "link": "https://n.news/1",
                "description": "공급 <b>계약</b>",
                "pubDate": "Sat, 30 May 2026 06:00:00 +0900",
            }
        ]
    }
    respx.get("https://openapi.naver.com/v1/search/news.json").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = NaverNewsClient(client_id="i", client_secret="s", timeout=5)
    items = client.search("삼성전자", stock_code="005930", display=5)
    assert items[0].title == "삼성전자 신규 계약"
    assert items[0].stock_code == "005930"
    assert items[0].corp_name == "삼성전자"
