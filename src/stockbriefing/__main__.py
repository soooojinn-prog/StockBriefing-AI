from __future__ import annotations

import logging
import sys

from anthropic import Anthropic

from stockbriefing.analysis.classifier import ImportanceClassifier
from stockbriefing.collectors.dart import DartClient
from stockbriefing.collectors.market import MarketClient
from stockbriefing.config import Settings
from stockbriefing.notifiers.discord import DiscordNotifier
from stockbriefing.notifiers.telegram import TelegramNotifier
from stockbriefing.orchestrator import BriefingOrchestrator
from stockbriefing.storage import FileStorage
from stockbriefing.watchlist import load_watchlist

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)


def build_orchestrator(settings: Settings) -> BriefingOrchestrator:
    watchlist = load_watchlist()
    notifiers = []
    if "discord" in settings.enabled_notifiers:
        notifiers.append(
            DiscordNotifier(settings.discord_webhook_url, settings.request_timeout_seconds)
        )
    if "telegram" in settings.enabled_notifiers:
        notifiers.append(
            TelegramNotifier(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                settings.request_timeout_seconds,
            )
        )
    return BriefingOrchestrator(
        dart=DartClient(settings.dart_api_key, settings.request_timeout_seconds),
        market=MarketClient(settings.ecos_api_key, settings.request_timeout_seconds),
        classifier=ImportanceClassifier(
            Anthropic(api_key=settings.anthropic_api_key), settings.classifier_model
        ),
        watchlist_codes={code for code, _ in watchlist},
        notifiers=notifiers,
        storage=FileStorage(),
        max_items=settings.max_items_per_section,
    )


def main() -> int:
    settings = Settings()
    if not settings.enabled_notifiers:
        logging.warning("no notifiers configured; report will be generated but not sent")
    orchestrator = build_orchestrator(settings)
    report = orchestrator.run()
    logging.info("briefing complete: %d high, %d medium", len(report.high), len(report.medium))
    return 0


if __name__ == "__main__":
    sys.exit(main())
