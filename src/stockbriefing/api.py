from __future__ import annotations

import glob
import os

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse


def create_app(orchestrator_factory, reports_dir: str = "reports") -> FastAPI:
    app = FastAPI(title="StockBriefing AI")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/reports/latest", response_class=PlainTextResponse)
    def latest():
        files = sorted(glob.glob(os.path.join(reports_dir, "*.md")))
        if not files:
            return PlainTextResponse("no reports yet", status_code=404)
        with open(files[-1], encoding="utf-8") as f:
            return f.read()

    @app.post("/run")
    def run():
        report = orchestrator_factory().run()
        return {
            "high": len(report.high),
            "medium": len(report.medium),
            "watchlist": len(report.watchlist),
        }

    return app
