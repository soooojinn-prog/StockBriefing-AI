from __future__ import annotations

from datetime import datetime

import httpx

from stockbriefing.models import Disclosure

DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"


class DartClient:
    def __init__(self, api_key: str, timeout: float = 20.0):
        self._api_key = api_key
        self._timeout = timeout

    def fetch_disclosures(self, start: datetime, end: datetime) -> list[Disclosure]:
        params = {
            "crtfc_key": self._api_key,
            "bgn_de": start.strftime("%Y%m%d"),
            "end_de": end.strftime("%Y%m%d"),
            "page_count": "100",
            "page_no": "1",
        }
        resp = httpx.get(DART_LIST_URL, params=params, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "000":
            return []
        out: list[Disclosure] = []
        for row in data.get("list", []):
            if not row.get("stock_code"):  # listed companies only
                continue
            out.append(
                Disclosure(
                    corp_name=row["corp_name"],
                    stock_code=row["stock_code"],
                    report_name=row["report_nm"],
                    rcept_no=row["rcept_no"],
                    rcept_dt=row["rcept_dt"],
                    flr_nm=row.get("flr_nm", ""),
                )
            )
        return out
