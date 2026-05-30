from __future__ import annotations

import json

from stockbriefing.analysis.guardrails import scrub_forbidden
from stockbriefing.models import ClassifiedItem, Disclosure, Importance

SYSTEM_PROMPT = (
    "너는 한국 주식시장 공시의 '시장 영향도'를 분류하는 분석 도구다. "
    "절대로 종목을 추천하거나, 주가를 예측하거나, 매수/매도/목표가를 언급하지 마라. "
    "너의 평가 대상은 '종목'이 아니라 '공시 자체의 시장 영향도'다. "
    "각 공시를 HIGH/MEDIUM/LOW 로 분류하라. "
    "HIGH: 공급계약·수주·유상증자·임상 결과·실적 서프라이즈 등 통상 주가 변동성을 크게 키우는 재료. "
    "MEDIUM: 영향이 제한적이거나 맥락 의존적인 공시. "
    "LOW: 정기보고서·기재정정 등 통상 영향이 미미한 공시. "
    "reason 은 사실 위주의 한 문장 한국어로, 추천/예측 표현 없이 작성하라."
)


def _build_user_prompt(disclosures: list[Disclosure]) -> str:
    rows = [
        {"rcept_no": d.rcept_no, "corp_name": d.corp_name, "report_name": d.report_name}
        for d in disclosures
    ]
    return (
        "다음 공시들을 분류해 JSON 배열로만 답하라. "
        '각 원소는 {"rcept_no", "importance"(HIGH|MEDIUM|LOW), "reason"} 형식이다.\n'
        + json.dumps(rows, ensure_ascii=False)
    )


def _extract_json(text: str) -> list[dict]:
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    return json.loads(text[start : end + 1])


class ImportanceClassifier:
    def __init__(self, client, model: str, max_tokens: int = 2000):
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def classify(self, disclosures: list[Disclosure]) -> list[ClassifiedItem]:
        if not disclosures:
            return []
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(disclosures)}],
        )
        raw = msg.content[0].text
        verdicts = {v["rcept_no"]: v for v in _extract_json(raw)}
        out: list[ClassifiedItem] = []
        for d in disclosures:
            v = verdicts.get(d.rcept_no)
            if not v:
                continue
            try:
                importance = Importance(v["importance"])
            except ValueError:
                importance = Importance.LOW
            out.append(
                ClassifiedItem(
                    kind="disclosure",
                    importance=importance,
                    reason=scrub_forbidden(str(v.get("reason", ""))),
                    title=d.report_name,
                    corp_name=d.corp_name,
                    stock_code=d.stock_code,
                    source_url=d.source_url,
                )
            )
        return out
