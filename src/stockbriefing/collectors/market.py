from __future__ import annotations

import datetime as dt

import httpx

from stockbriefing.models import MarketIndicator

# ECOS USD/KRW daily exchange rate: stat code 731Y001, item 0000001
ECOS_FX_STAT = "731Y001"
ECOS_FX_ITEM = "0000001"


class MarketClient:
    def __init__(self, ecos_api_key: str, timeout: float = 20.0):
        self._key = ecos_api_key
        self._timeout = timeout

    def fetch_indicators(self) -> list[MarketIndicator]:
        out: list[MarketIndicator] = []
        fx = self._fetch_usdkrw()
        if fx is not None:
            out.append(fx)
        return out

    def _fetch_usdkrw(self) -> MarketIndicator | None:
        today = dt.date.today().strftime("%Y%m%d")
        start = (dt.date.today() - dt.timedelta(days=10)).strftime("%Y%m%d")
        url = (
            f"https://ecos.bok.or.kr/api/StatisticSearch/{self._key}/json/kr/1/10/"
            f"{ECOS_FX_STAT}/D/{start}/{today}/{ECOS_FX_ITEM}"
        )
        try:
            resp = httpx.get(url, timeout=self._timeout)
            resp.raise_for_status()
            rows = resp.json().get("StatisticSearch", {}).get("row", [])
            if not rows:
                return None
            latest = rows[-1]
            return MarketIndicator(name="원/달러 환율", value=str(latest["DATA_VALUE"]), unit="원")
        except (httpx.HTTPError, KeyError, ValueError):
            return None
