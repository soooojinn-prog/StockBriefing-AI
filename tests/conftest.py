import os

import pytest

os.environ.setdefault("DART_API_KEY", "test-dart-key")
os.environ.setdefault("NAVER_CLIENT_ID", "test-naver-id")
os.environ.setdefault("NAVER_CLIENT_SECRET", "test-naver-secret")
os.environ.setdefault("ECOS_API_KEY", "test-ecos-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://discord.test/webhook")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456")


@pytest.fixture
def anyio_backend():
    return "asyncio"
