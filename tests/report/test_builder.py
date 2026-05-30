from datetime import datetime

from stockbriefing.models import ClassifiedItem, Importance, MarketIndicator
from stockbriefing.report.builder import ReportBuilder


def _item(code, imp):
    return ClassifiedItem(
        kind="disclosure", importance=imp, reason="r", title="t", corp_name="c", stock_code=code
    )


def test_build_splits_sections_and_watchlist():
    items = [
        _item("005930", Importance.HIGH),
        _item("111111", Importance.MEDIUM),
        _item("222222", Importance.LOW),
    ]
    rb = ReportBuilder(watchlist_codes={"005930"}, max_items=10)
    report = rb.build(
        datetime(2026, 5, 30, 8, 0),
        indicators=[MarketIndicator(name="코스피", value="2650")],
        classified=items,
    )
    assert len(report.high) == 1
    assert len(report.medium) == 1
    assert [i.stock_code for i in report.watchlist] == ["005930"]
    assert "투자 자문" in report.to_markdown()


def test_build_caps_section_size():
    items = [_item(f"{i:06d}", Importance.HIGH) for i in range(20)]
    rb = ReportBuilder(watchlist_codes=set(), max_items=5)
    report = rb.build(datetime(2026, 5, 30, 8, 0), indicators=[], classified=items)
    assert len(report.high) == 5
