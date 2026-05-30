from stockbriefing.analysis.guardrails import FORBIDDEN, scrub_forbidden


def test_scrub_replaces_recommendation_phrases():
    text = "이 종목 매수 추천합니다. 목표가 10만원."
    cleaned = scrub_forbidden(text)
    assert "매수 추천" not in cleaned
    assert "목표가" not in cleaned
    assert "[표현 제거됨]" in cleaned


def test_scrub_keeps_neutral_factual_text():
    text = "단일판매ㆍ공급계약 체결 공시가 접수되었습니다."
    assert scrub_forbidden(text) == text


def test_forbidden_list_nonempty():
    assert "매수" in FORBIDDEN
