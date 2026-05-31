from datetime import datetime

from stockbriefing.models import ClassifiedItem, Disclosure, Importance, MarketIndicator
from stockbriefing.report.builder import ReportBuilder


def _item(code, imp):
    return ClassifiedItem(
        kind="disclosure", importance=imp, reason="r", title="t", corp_name="c", stock_code=code
    )


def _disc(code, name="공시"):
    return Disclosure(
        corp_name="c", stock_code=code, report_name=name, rcept_no=code, rcept_dt="20260530", flr_nm="c"
    )


def test_build_keeps_high_only_from_classified():
    classified = [
        _item("005930", Importance.HIGH),
        _item("111111", Importance.MEDIUM),
        _item("222222", Importance.LOW),
    ]
    rb = ReportBuilder(watchlist_codes={"005930"}, max_items=10)
    report = rb.build(
        datetime(2026, 5, 30, 8, 0),
        indicators=[MarketIndicator(name="코스피", value="2650")],
        classified=classified,
        disclosures=[],
    )
    assert len(report.high) == 1  # MEDIUM/LOW excluded
    assert "중요도 중간" not in report.to_markdown()
    assert "투자 자문" in report.to_markdown()


def test_watchlist_is_independent_of_classification():
    # A watchlist stock with only a LOW (excluded) disclosure must still appear,
    # sourced directly from raw disclosures — not from the classified list.
    rb = ReportBuilder(watchlist_codes={"005930"}, max_items=10)
    report = rb.build(
        datetime(2026, 5, 30, 8, 0),
        indicators=[],
        classified=[],  # nothing classified HIGH/MEDIUM
        disclosures=[_disc("005930", "분기보고서"), _disc("999999", "남의 종목")],
    )
    assert [d.stock_code for d in report.watchlist] == ["005930"]
    assert "분기보고서" in report.to_markdown()


def test_build_populates_earnings_and_ownership_sections():
    rb = ReportBuilder(watchlist_codes=set(), max_items=10)
    report = rb.build(
        datetime(2026, 5, 30, 8, 0),
        indicators=[],
        classified=[],
        disclosures=[
            _disc("005930", "영업(잠정)실적(공정공시)"),
            _disc("000660", "주식등의대량보유상황보고서(일반)"),
            _disc("111111", "단일판매ㆍ공급계약체결"),
        ],
    )
    assert [d.stock_code for d in report.earnings] == ["005930"]
    assert [d.stock_code for d in report.ownership] == ["000660"]
    md = report.to_markdown()
    assert "실적·손익" in md and "대량보유" in md


def test_build_caps_section_size():
    items = [_item(f"{i:06d}", Importance.HIGH) for i in range(20)]
    rb = ReportBuilder(watchlist_codes=set(), max_items=5)
    report = rb.build(datetime(2026, 5, 30, 8, 0), indicators=[], classified=items, disclosures=[])
    assert len(report.high) == 5
