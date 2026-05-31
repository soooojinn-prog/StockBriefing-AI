"""Shared helper for parsing a JSON array out of an LLM response."""

from __future__ import annotations

import json


def extract_json_array(text: str) -> list[dict]:
    """Parse a JSON array from model output, salvaging truncated responses."""
    start = text.find("[")
    if start == -1:
        return []
    snippet = text[start:]
    end = snippet.rfind("]")
    if end != -1:
        try:
            return json.loads(snippet[: end + 1])
        except json.JSONDecodeError:
            pass
    # Response was cut off mid-array: keep everything up to the last complete
    # object and close the array ourselves.
    last_obj = snippet.rfind("}")
    if last_obj == -1:
        return []
    try:
        return json.loads(snippet[: last_obj + 1] + "]")
    except json.JSONDecodeError:
        return []
