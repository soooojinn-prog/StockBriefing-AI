import httpx
import respx

from stockbriefing.collectors.market import MarketClient


@respx.mock
def test_fetch_indicators_parses_usdkrw():
    payload = {
        "StatisticSearch": {
            "row": [{"TIME": "20260529", "DATA_VALUE": "1365.5", "ITEM_NAME1": "원/달러"}]
        }
    }
    respx.get(url__regex=r"https://ecos\.bok\.or\.kr/api/StatisticSearch/.*").mock(
        return_value=httpx.Response(200, json=payload)
    )
    client = MarketClient(ecos_api_key="k", timeout=5)
    inds = client.fetch_indicators()
    fx = [i for i in inds if i.name == "원/달러 환율"]
    assert fx and fx[0].value == "1365.5"


@respx.mock
def test_fetch_indicators_degrades_on_error():
    respx.get(url__regex=r"https://ecos\.bok\.or\.kr/api/.*").mock(
        return_value=httpx.Response(500)
    )
    client = MarketClient(ecos_api_key="k", timeout=5)
    assert client.fetch_indicators() == []
