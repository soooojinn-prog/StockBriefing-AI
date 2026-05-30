from datetime import datetime

import httpx
import respx

from stockbriefing.collectors.dart import DartClient


@respx.mock
def test_fetch_disclosures_parses_list():
    payload = {
        "status": "000",
        "message": "정상",
        "list": [
            {
                "corp_name": "삼성전자",
                "stock_code": "005930",
                "report_nm": "단일판매ㆍ공급계약체결",
                "rcept_no": "20260530000123",
                "rcept_dt": "20260530",
                "flr_nm": "삼성전자",
            },
            {
                "corp_name": "비상장사",
                "stock_code": "",
                "report_nm": "기타",
                "rcept_no": "20260530000999",
                "rcept_dt": "20260530",
                "flr_nm": "비상장사",
            },
        ],
    }
    respx.get("https://opendart.fss.or.kr/api/list.json").mock(
        return_value=httpx.Response(200, json=payload)
    )

    client = DartClient(api_key="k", timeout=5)
    out = client.fetch_disclosures(
        datetime(2026, 5, 29, 15, 30), datetime(2026, 5, 30, 8, 0)
    )

    assert len(out) == 1  # listed-only (stock_code present) kept
    assert out[0].corp_name == "삼성전자"


@respx.mock
def test_fetch_disclosures_handles_no_data_status():
    respx.get("https://opendart.fss.or.kr/api/list.json").mock(
        return_value=httpx.Response(
            200, json={"status": "013", "message": "조회된 데이타가 없습니다."}
        )
    )
    client = DartClient(api_key="k", timeout=5)
    assert client.fetch_disclosures(datetime(2026, 5, 29), datetime(2026, 5, 30)) == []
