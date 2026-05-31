from datetime import datetime

from stockbriefing.models import (
    ClassifiedItem,
    Disclosure,
    Importance,
    MarketIndicator,
    NewsItem,
    Report,
    previous_market_close,
)


def test_disclosure_source_url_built_from_rcept_no():
    d = Disclosure(
        corp_name="삼성전자",
        stock_code="005930",
        report_name="단일판매ㆍ공급계약체결",
        rcept_no="20260530000123",
        rcept_dt="20260530",
        flr_nm="삼성전자",
    )
    assert d.source_url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260530000123"


def test_classified_item_carries_importance_and_reason():
    d = Disclosure(
        corp_name="A",
        stock_code="000001",
        report_name="유상증자결정",
        rcept_no="1",
        rcept_dt="20260530",
        flr_nm="A",
    )
    c = ClassifiedItem(
        kind="disclosure",
        importance=Importance.HIGH,
        reason="자금조달 규모가 시총 대비 큼",
        title=d.report_name,
        corp_name=d.corp_name,
        stock_code=d.stock_code,
        source_url=d.source_url,
    )
    assert c.importance == Importance.HIGH


def test_news_item_defaults():
    n = NewsItem(title="t", link="l")
    assert n.stock_code == "" and n.corp_name == ""


def test_report_renders_disclaimer_always():
    r = Report(
        generated_at=datetime(2026, 5, 30, 8, 0),
        indicators=[MarketIndicator(name="코스피", value="2650")],
        high=[],
        watchlist=[],
    )
    text = r.to_markdown()
    assert "투자 자문" in text and "추천이 아닙니다" in text


def test_previous_market_close_on_friday_morning_is_thursday():
    now = datetime(2026, 5, 29, 8, 0)  # Friday
    assert previous_market_close(now) == datetime(2026, 5, 28, 15, 30)


def test_previous_market_close_on_monday_morning_is_friday():
    now = datetime(2026, 6, 1, 8, 0)  # Monday
    assert previous_market_close(now) == datetime(2026, 5, 29, 15, 30)
