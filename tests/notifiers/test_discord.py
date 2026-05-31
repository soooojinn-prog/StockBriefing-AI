from datetime import datetime

import httpx
import respx

from stockbriefing.models import Report
from stockbriefing.notifiers.discord import DiscordNotifier


@respx.mock
def test_discord_send_posts_content():
    route = respx.post("https://discord.test/webhook").mock(
        return_value=httpx.Response(204)
    )
    report = Report(
        generated_at=datetime(2026, 5, 30, 8, 0),
        indicators=[],
        high=[],
        watchlist=[],
    )
    DiscordNotifier(webhook_url="https://discord.test/webhook").send(report)
    assert route.called
    body = route.calls[0].request.content.decode()
    assert "StockBriefing" in body
