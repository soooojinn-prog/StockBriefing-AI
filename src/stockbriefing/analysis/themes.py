"""Keyword-based theme filtering over raw DART disclosures (no LLM, no extra API).

These are independent views over the whole-market disclosure list, used to surface
two themed sections in the briefing:

- earnings: 실적·손익구조 변동 공시 (흑자전환이 이 안에서 나옴)
- ownership: 대량보유·지분 변동 공시 (외국인·기관 매집 등 수급 신호)

Note: the disclosure *list* API exposes only the report title, so we can reliably
identify the *category* but not the *direction* (흑자 vs 적자) or the holder's
nationality (외국인 여부). Confirming those requires parsing the filing body — a
planned v2 refinement.
"""

from __future__ import annotations

from stockbriefing.models import Disclosure

# "발행실적" 같은 비실적 공시를 피하려고 구체적 패턴만 사용.
EARNINGS_KEYWORDS = ("손익구조", "영업(잠정)실적", "잠정실적", "결산실적")
OWNERSHIP_KEYWORDS = ("대량보유", "특정증권등소유", "주요주주")


def _matches(name: str, keywords: tuple[str, ...]) -> bool:
    return any(k in name for k in keywords)


def filter_earnings(disclosures: list[Disclosure]) -> list[Disclosure]:
    return [d for d in disclosures if _matches(d.report_name, EARNINGS_KEYWORDS)]


def filter_ownership(disclosures: list[Disclosure]) -> list[Disclosure]:
    return [d for d in disclosures if _matches(d.report_name, OWNERSHIP_KEYWORDS)]
