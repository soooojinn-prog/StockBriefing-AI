from __future__ import annotations

from typing import Protocol

from stockbriefing.models import Report


class Notifier(Protocol):
    name: str

    def send(self, report: Report) -> None: ...


def chunk_text(text: str, limit: int) -> list[str]:
    """Split text on line boundaries so each chunk stays under ``limit`` chars."""
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit and current:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current)
    return chunks
