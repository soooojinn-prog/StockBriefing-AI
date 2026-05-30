from __future__ import annotations

import re

FORBIDDEN = [
    "매수 추천",
    "매도 추천",
    "매수",
    "매도",
    "추천 종목",
    "추천합니다",
    "추천 드립니다",
    "목표가",
    "사세요",
    "파세요",
    "오를 것",
    "오를것",
    "상승할 것",
    "급등 예상",
    "단언",
    "확실히 오른",
    "보장",
]
_REPLACEMENT = "[표현 제거됨]"
_PATTERN = re.compile("|".join(re.escape(w) for w in sorted(FORBIDDEN, key=len, reverse=True)))


def scrub_forbidden(text: str) -> str:
    """Replace any recommendation/prediction phrasing with a neutral marker."""
    return _PATTERN.sub(_REPLACEMENT, text)
