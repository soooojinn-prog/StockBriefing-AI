"""Summarize watchlist news headlines into one neutral line each (cheap model)."""

from __future__ import annotations

import json

from stockbriefing.analysis.guardrails import scrub_forbidden
from stockbriefing.analysis.jsonutil import extract_json_array
from stockbriefing.models import NewsItem

SYSTEM_PROMPT = (
    "너는 한국 주식 관련 뉴스를 사실 위주로 요약하는 도구다. "
    "각 뉴스를 한국어 한 문장(40자 이내)으로 요약하라. "
    "절대 매수/매도/추천/목표가/주가 예측 표현을 쓰지 마라. 사실만 전달하라."
)


def _build_prompt(news: list[NewsItem]) -> str:
    rows = [{"i": i, "title": n.title, "desc": n.description} for i, n in enumerate(news)]
    return (
        "다음 뉴스들을 각각 요약해 JSON 배열로만 답하라. "
        '각 원소는 {"i"(번호), "summary"(40자 이내 한국어 한 문장)} 형식이다.\n'
        + json.dumps(rows, ensure_ascii=False)
    )


class NewsSummarizer:
    def __init__(self, client, model: str, max_tokens: int = 2000):
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def summarize(self, news: list[NewsItem]) -> list[NewsItem]:
        """Return copies of ``news`` with ``summary`` filled. Falls back to the
        original items (no summary) on any error, so the caller degrades gracefully."""
        if not news:
            return news
        try:
            msg = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_prompt(news)}],
            )
            verdicts = {v["i"]: v.get("summary", "") for v in extract_json_array(msg.content[0].text)}
        except Exception:  # noqa: BLE001 — summary is best-effort
            return news
        out: list[NewsItem] = []
        for i, item in enumerate(news):
            summary = scrub_forbidden(str(verdicts.get(i, "")))
            out.append(item.model_copy(update={"summary": summary}))
        return out
