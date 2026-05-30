from __future__ import annotations

import os

import yaml


def load_watchlist(path: str = "watchlist.yaml") -> list[tuple[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [(str(s["code"]), str(s["name"])) for s in data.get("stocks", [])]
