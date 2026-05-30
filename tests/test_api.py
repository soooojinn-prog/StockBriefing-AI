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


def test_health_ok():
    app = create_app(orchestrator_factory=lambda: _Orch(), reports_dir="reports")
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_run_triggers_orchestrator():
    app = create_app(orchestrator_factory=lambda: _Orch(), reports_dir="reports")
    client = TestClient(app)
    resp = client.post("/run")
    assert resp.status_code == 200
    assert resp.json()["high"] == 0
