from stockbriefing.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "abc")
    monkeypatch.setenv("NAVER_CLIENT_ID", "id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ECOS_API_KEY", "ecos")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anth")
    s = Settings()
    assert s.dart_api_key == "abc"
    assert s.naver_client_id == "id"
    assert s.classifier_model.startswith("claude")


def test_enabled_notifiers_reflects_present_secrets(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://x")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    s = Settings(_env_file=None)
    assert "discord" in s.enabled_notifiers
    assert "telegram" not in s.enabled_notifiers
