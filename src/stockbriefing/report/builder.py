from __future__ import annotations

from datetime import datetime

from stockbriefing.models import ClassifiedItem, Importance, MarketIndicator, Report


class ReportBuilder:
    def __init__(self, watchlist_codes: set[str], max_items: int = 15):
        self._watchlist = watchlist_codes
        self._max = max_items

    def build(
        self,
        generated_at: datetime,
        indicators: list[MarketIndicator],
        classified: list[ClassifiedItem],
    ) -> Report:
        high = [c for c in classified if c.importance == Importance.HIGH][: self._max]
        medium = [c for c in classified if c.importance == Importance.MEDIUM][: self._max]
        watchlist = [c for c in classified if c.stock_code in self._watchlist][: self._max]
        return Report(
            generated_at=generated_at,
            indicators=indicators,
            high=high,
            medium=medium,
            watchlist=watchlist,
        )
