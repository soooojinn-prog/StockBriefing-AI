from stockbriefing.models import Disclosure, NewsItem
from stockbriefing.watchlist_monitor import build_watchlist_entries


def _disc(code, name="공시"):
    return Disclosure(
        corp_name="c", stock_code=code, report_name=name, rcept_no=code, rcept_dt="20260530", flr_nm="c"
    )


class _NewsStub:
    def search(self, keyword, stock_code="", display=3):
        return [NewsItem(title=f"{keyword} 뉴스", link=f"https://n/{stock_code}", stock_code=stock_code)]


class _SummarizerStub:
    def summarize(self, news):
        return [n.model_copy(update={"summary": "요약"}) for n in news]


def test_entry_combines_disclosures_and_summarized_news():
    entries = build_watchlist_entries(
        watchlist=[("005930", "삼성전자")],
        disclosures=[_disc("005930", "분기보고서"), _disc("999999", "남의공시")],
        news_client=_NewsStub(),
        summarizer=_SummarizerStub(),
    )
    assert len(entries) == 1
    e = entries[0]
    assert e.name == "삼성전자"
    assert [d.report_name for d in e.disclosures] == ["분기보고서"]  # 남의공시 제외
    assert e.news[0].summary == "요약"


def test_stock_with_no_disclosure_or_news_is_omitted():
    entries = build_watchlist_entries(
        watchlist=[("005930", "삼성전자")],
        disclosures=[],
        news_client=None,  # no news
        summarizer=None,
    )
    assert entries == []


def test_news_fetch_failure_degrades_gracefully():
    class _BoomNews:
        def search(self, *a, **k):
            raise RuntimeError("naver down")

    entries = build_watchlist_entries(
        watchlist=[("005930", "삼성전자")],
        disclosures=[_disc("005930", "분기보고서")],
        news_client=_BoomNews(),
        summarizer=None,
    )
    # Disclosure still surfaces even though news fetching blew up.
    assert len(entries) == 1
    assert entries[0].news == []
