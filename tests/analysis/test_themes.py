from stockbriefing.analysis.themes import filter_earnings, filter_ownership
from stockbriefing.models import Disclosure


def _disc(name, code="000001"):
    return Disclosure(
        corp_name="c", stock_code=code, report_name=name, rcept_no=name, rcept_dt="20260530", flr_nm="c"
    )


def test_filter_earnings_matches_pnl_disclosures():
    discs = [
        _disc("매출액또는손익구조30%(대규모법인은15%)이상변동"),
        _disc("영업(잠정)실적(공정공시)"),
        _disc("단일판매ㆍ공급계약체결"),
    ]
    out = filter_earnings(discs)
    assert len(out) == 2
    assert all("공급계약" not in d.report_name for d in out)


def test_filter_ownership_matches_holding_disclosures():
    discs = [
        _disc("주식등의대량보유상황보고서(일반)"),
        _disc("임원ㆍ주요주주특정증권등소유상황보고서"),
        _disc("분기보고서"),
    ]
    out = filter_ownership(discs)
    assert len(out) == 2
    assert all("분기보고서" not in d.report_name for d in out)
