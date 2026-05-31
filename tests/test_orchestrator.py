from datetime import datetime

from stockbriefing.models import (
    ClassifiedItem,
    Disclosure,
    Importance,
    MarketIndicator,
    Report,
)
from stockbriefing.orchestrator import BriefingOrchestrator


class _DartStub:
    def fetch_disclosures(self, start, end):
        return [
            Disclosure(
                corp_name="A",
                stock_code="005930",
                report_name="공급계약",
                rcept_no="1",
                rcept_dt="20260530",
                flr_nm="A",
            )
        ]


class _MarketStub:
    def fetch_indicators(self):
        return [MarketIndicator(name="코스피", value="2650")]


class _ClassifierStub:
    def classify(self, disclosures):
        if not disclosures:
            return []
        return [
            ClassifiedItem(
                kind="disclosure",
                importance=Importance.HIGH,
                reason="r",
                title="공급계약",
                corp_name="A",
                stock_code="005930",
            )
        ]


class _RecordingNotifier:
    name = "rec"

    def __init__(self):
        self.sent = []

    def send(self, report):
        self.sent.append(report)


def test_run_builds_and_sends_report():
    notifier = _RecordingNotifier()
    orch = BriefingOrchestrator(
        dart=_DartStub(),
        market=_MarketStub(),
        classifier=_ClassifierStub(),
        watchlist_codes={"005930"},
        notifiers=[notifier],
        storage=None,
        max_items=15,
    )
    report = orch.run(now=datetime(2026, 5, 30, 8, 0))
    assert isinstance(report, Report)
    assert len(notifier.sent) == 1
    assert report.high[0].corp_name == "A"
    # Watchlist view is sourced from raw disclosures, independent of classification.
    assert [d.stock_code for d in report.watchlist] == ["005930"]


def test_run_continues_when_collector_fails():
    class _BoomDart:
        def fetch_disclosures(self, start, end):
            raise RuntimeError("dart down")

    notifier = _RecordingNotifier()
    orch = BriefingOrchestrator(
        dart=_BoomDart(),
        market=_MarketStub(),
        classifier=_ClassifierStub(),
        watchlist_codes=set(),
        notifiers=[notifier],
        storage=None,
        max_items=15,
    )
    report = orch.run(now=datetime(2026, 5, 30, 8, 0))
    assert report.high == []  # no disclosures, but run completed
    assert len(notifier.sent) == 1
