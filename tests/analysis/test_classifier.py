import json

from stockbriefing.analysis.classifier import ImportanceClassifier
from stockbriefing.models import Disclosure, Importance


class _FakeMessage:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


class _FakeMessages:
    def __init__(self, text):
        self._text = text

    def create(self, **kwargs):
        return _FakeMessage(self._text)


class _FakeAnthropic:
    def __init__(self, text):
        self.messages = _FakeMessages(text)


def _disc(rcept_no, name):
    return Disclosure(
        corp_name="A",
        stock_code="000001",
        report_name=name,
        rcept_no=rcept_no,
        rcept_dt="20260530",
        flr_nm="A",
    )


def test_classify_maps_importance_and_scrubs_reason():
    fake_json = json.dumps(
        [
            {"rcept_no": "1", "importance": "HIGH", "reason": "공급계약 규모 큼. 매수 추천."},
            {"rcept_no": "2", "importance": "LOW", "reason": "정기 보고서"},
        ]
    )
    clf = ImportanceClassifier(client=_FakeAnthropic(fake_json), model="m")
    items = clf.classify([_disc("1", "공급계약"), _disc("2", "분기보고서")])
    by_imp = {i.importance: i for i in items}
    assert by_imp[Importance.HIGH].title == "공급계약"
    assert "매수 추천" not in by_imp[Importance.HIGH].reason  # guardrail applied


def test_classify_empty_input_returns_empty_without_calling_llm():
    clf = ImportanceClassifier(client=None, model="m")
    assert clf.classify([]) == []
