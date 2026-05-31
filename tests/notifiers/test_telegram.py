from datetime import datetime

import httpx
import respx

from stockbriefing.models import Report
from stockbriefing.notifiers.telegram import TelegramNotifier


@respx.mock
def test_telegram_send_posts_message():
    route = respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True})
    )
    report = Report(
        generated_at=datetime(2026, 5, 30, 8, 0),
        indicators=[],
        high=[],
        watchlist=[],
    )
    TelegramNotifier(bot_token="TOKEN", chat_id="42").send(report)
    assert route.called
    body = route.calls[0].request.content.decode()
    assert "42" in body and "StockBriefing" in body
