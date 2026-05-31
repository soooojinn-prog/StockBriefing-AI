"""Assemble the independent watchlist view: per-stock disclosures + overnight news.

This is deliberately separate from the market-wide importance classifier — it
surfaces everything happening to the user's own stocks regardless of importance.
"""

from __future__ import annotations

import logging

from stockbriefing.models import Disclosure, NewsItem, WatchlistEntry

log = logging.getLogger("stockbriefing")


def build_watchlist_entries(
    watchlist: list[tuple[str, str]],
    disclosures: list[Disclosure],
    news_client=None,
    summarizer=None,
    news_per_stock: int = 3,
) -> list[WatchlistEntry]:
    """Build one entry per watchlist stock that has any disclosure or news.

    `news_client` and `summarizer` are optional; missing/failing either just means
    fewer news items, never a crash."""
    by_code: dict[str, list[Disclosure]] = {}
    for d in disclosures:
        by_code.setdefault(d.stock_code, []).append(d)

    entries: list[WatchlistEntry] = []
    all_news: list[NewsItem] = []
    pending: list[WatchlistEntry] = []

    for code, name in watchlist:
        news: list[NewsItem] = []
        if news_client is not None:
            try:
                news = news_client.search(name, stock_code=code, display=news_per_stock)
            except Exception:  # noqa: BLE001 — news is best-effort
                log.exception("news fetch failed for %s", name)
                news = []
        entry = WatchlistEntry(name=name, stock_code=code, disclosures=by_code.get(code, []), news=news)
        all_news.extend(news)
        pending.append(entry)

    # Summarize all watchlist news in a single batched call.
    if summarizer is not None and all_news:
        summarized = summarizer.summarize(all_news)
        by_link = {n.link: n for n in summarized}
        pending = [
            entry.model_copy(update={"news": [by_link.get(n.link, n) for n in entry.news]})
            for entry in pending
        ]

    for entry in pending:
        if entry.disclosures or entry.news:
            entries.append(entry)
    return entries
