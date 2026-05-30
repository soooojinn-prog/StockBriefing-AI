from datetime import datetime

from fastapi.testclient import TestClient

from stockbriefing.api import create_app
from stockbriefing.models import Report


class _Orch:
    def run(self, now=None):
        return Report(
            generated_at=datetime(2026, 5, 30, 8, 0),
            indicators=[],
            high=[],
            medium=[],
            watchlist=[],
        )


def test_health_ok_without_auth():
    app = create_app(orchestrator_factory=lambda: _Orch(), reports_dir="reports")
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_run_with_valid_token_triggers_orchestrator():
    app = create_app(orchestrator_factory=lambda: _Orch(), api_token="secret")
    client = TestClient(app)
    resp = client.post("/run", headers={"Authorization": "Bearer secret"})
    assert resp.status_code == 200
    assert resp.json()["high"] == 0


def test_run_without_token_is_unauthorized():
    app = create_app(orchestrator_factory=lambda: _Orch(), api_token="secret")
    client = TestClient(app)
    assert client.post("/run").status_code == 401
    assert client.post("/run", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_protected_routes_disabled_when_no_token_configured():
    app = create_app(orchestrator_factory=lambda: _Orch())
    client = TestClient(app)
    assert client.post("/run").status_code == 503
    assert client.get("/reports/latest").status_code == 503
