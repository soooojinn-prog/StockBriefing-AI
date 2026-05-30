from __future__ import annotations

import os
from typing import Protocol

from stockbriefing.models import Report


class StorageInterface(Protocol):
    def save(self, report: Report) -> str: ...


class FileStorage:
    def __init__(self, directory: str = "reports"):
        self._dir = directory

    def save(self, report: Report) -> str:
        os.makedirs(self._dir, exist_ok=True)
        path = os.path.join(self._dir, f"{report.generated_at:%Y-%m-%d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())
        return path
