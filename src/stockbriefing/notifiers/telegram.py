from __future__ import annotations

import httpx

from stockbriefing.models import Report
from stockbriefing.notifiers.base import chunk_text

TELEGRAM_LIMIT = 4000


class TelegramNotifier:
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, timeout: float = 20.0):
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id
        self._timeout = timeout

    def send(self, report: Report) -> None:
        for chunk in chunk_text(report.to_markdown(), TELEGRAM_LIMIT):
            resp = httpx.post(
                self._url,
                json={"chat_id": self._chat_id, "text": chunk},
                timeout=self._timeout,
            )
            resp.raise_for_status()
