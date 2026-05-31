from __future__ import annotations

from datetime import datetime

from stockbriefing.analysis.themes import filter_earnings, filter_ownership
from stockbriefing.models import (
    ClassifiedItem,
    Disclosure,
    Importance,
    MarketIndicator,
    Report,
    WatchlistEntry,
)


class ReportBuilder:
    def __init__(self, max_items: int = 15):
        self._max = max_items

    def build(
        self,
        generated_at: datetime,
        indicators: list[MarketIndicator],
        classified: list[ClassifiedItem],
        disclosures: list[Disclosure],
        watchlist: list[WatchlistEntry],
    ) -> Report:
        # Market radar: only HIGH-importance disclosures, whole-market.
        high = [c for c in classified if c.importance == Importance.HIGH][: self._max]
        # Theme views over all disclosures (keyword-based).
        earnings = filter_earnings(disclosures)[: self._max]
        ownership = filter_ownership(disclosures)[: self._max]
        return Report(
            generated_at=generated_at,
            indicators=indicators,
            high=high,
            earnings=earnings,
            ownership=ownership,
            watchlist=watchlist[: self._max],
        )
