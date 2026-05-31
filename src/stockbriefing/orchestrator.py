from __future__ import annotations

import logging
from datetime import datetime

from stockbriefing.models import Report, previous_market_close
from stockbriefing.report.builder import ReportBuilder

log = logging.getLogger("stockbriefing")


class BriefingOrchestrator:
    def __init__(
        self,
        dart,
        market,
        classifier,
        watchlist_codes,
        notifiers,
        storage=None,
        max_items: int = 15,
    ):
        self._dart = dart
        self._market = market
        self._classifier = classifier
        self._builder = ReportBuilder(watchlist_codes=set(watchlist_codes), max_items=max_items)
        self._notifiers = notifiers
        self._storage = storage

    def run(self, now: datetime | None = None) -> Report:
        now = now or datetime.now()
        start = previous_market_close(now)

        disclosures = self._safe(
            lambda: self._dart.fetch_disclosures(start, now), "dart", default=[]
        )
        indicators = self._safe(self._market.fetch_indicators, "market", default=[])
        classified = self._safe(
            lambda: self._classifier.classify(disclosures), "classifier", default=[]
        )

        report = self._builder.build(
            now, indicators=indicators, classified=classified, disclosures=disclosures
        )

        if self._storage is not None:
            self._safe(lambda: self._storage.save(report), "storage", default=None)

        for notifier in self._notifiers:
            try:
                notifier.send(report)
            except Exception:  # noqa: BLE001
                log.exception("notifier %s failed", getattr(notifier, "name", "?"))
        return report

    @staticmethod
    def _safe(fn, label, default):
        try:
            return fn()
        except Exception:  # noqa: BLE001
            log.exception("%s step failed", label)
            return default
