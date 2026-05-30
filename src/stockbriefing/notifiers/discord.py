from __future__ import annotations

import httpx

from stockbriefing.models import Report
from stockbriefing.notifiers.base import chunk_text

DISCORD_LIMIT = 1900


class DiscordNotifier:
    name = "discord"

    def __init__(self, webhook_url: str, timeout: float = 20.0):
        self._url = webhook_url
        self._timeout = timeout

    def send(self, report: Report) -> None:
        for chunk in chunk_text(report.to_markdown(), DISCORD_LIMIT):
            resp = httpx.post(self._url, json={"content": chunk}, timeout=self._timeout)
            resp.raise_for_status()
