import json

from stockbriefing.analysis.news_summarizer import NewsSummarizer
from stockbriefing.models import NewsItem


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


def test_summarize_fills_summary_and_scrubs():
    payload = json.dumps(
        [
            {"i": 0, "summary": "신규 계약 체결 소식. 매수 추천."},
            {"i": 1, "summary": "신제품 출시 발표"},
        ]
    )
    s = NewsSummarizer(client=_FakeAnthropic(payload), model="m")
    news = [NewsItem(title="a", link="l1"), NewsItem(title="b", link="l2")]
    out = s.summarize(news)
    assert "[표현 제거됨]" in out[0].summary  # guardrail applied
    assert "매수 추천" not in out[0].summary
    assert out[1].summary == "신제품 출시 발표"


def test_summarize_degrades_to_unsummarized_on_error():
    class _Boom:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("llm down")

    out = NewsSummarizer(client=_Boom(), model="m").summarize([NewsItem(title="a", link="l")])
    assert out[0].summary == ""


def test_summarize_empty_returns_empty_without_call():
    assert NewsSummarizer(client=None, model="m").summarize([]) == []
