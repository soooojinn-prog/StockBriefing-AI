from __future__ import annotations

import glob
import hmac
import os

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import PlainTextResponse


def create_app(orchestrator_factory, reports_dir: str = "reports", api_token: str = "") -> FastAPI:
    app = FastAPI(title="StockBriefing AI")

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        # No token configured => the cost/data routes are disabled, not open.
        if not api_token:
            raise HTTPException(status_code=503, detail="API auth not configured")
        expected = f"Bearer {api_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get(
        "/reports/latest",
        response_class=PlainTextResponse,
        dependencies=[Depends(require_auth)],
    )
    def latest():
        files = sorted(glob.glob(os.path.join(reports_dir, "*.md")))
        if not files:
            return PlainTextResponse("no reports yet", status_code=404)
        with open(files[-1], encoding="utf-8") as f:
            return f.read()

    @app.post("/run", dependencies=[Depends(require_auth)])
    def run():
        report = orchestrator_factory().run()
        return {
            "high": len(report.high),
            "watchlist": len(report.watchlist),
        }

    return app


def default_app() -> FastAPI:
    """Factory for ``uvicorn stockbriefing.api:default_app --factory``."""
    from stockbriefing.__main__ import build_orchestrator
    from stockbriefing.config import Settings

    settings = Settings()
    return create_app(
        orchestrator_factory=lambda: build_orchestrator(settings),
        api_token=settings.api_token,
    )
