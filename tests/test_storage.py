from datetime import datetime

from stockbriefing.models import Report
from stockbriefing.storage import FileStorage


def test_file_storage_writes_markdown(tmp_path):
    report = Report(
        generated_at=datetime(2026, 5, 30, 8, 0),
        indicators=[],
        high=[],
        watchlist=[],
    )
    store = FileStorage(directory=str(tmp_path))
    path = store.save(report)
    assert path.endswith("2026-05-30.md")
    assert "StockBriefing" in (tmp_path / "2026-05-30.md").read_text(encoding="utf-8")
