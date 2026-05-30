# StockBriefing AI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a stateless daily pipeline that scans overnight DART disclosures + Naver news + market indicators, classifies their market-impact importance with Claude (never recommending stocks), renders a Korean briefing report, and sends it to Discord + Telegram at 08:00 KST on weekdays.

**Architecture:** A `BriefingOrchestrator` coordinates three collectors (DART/Naver/ECOS), an LLM `ImportanceClassifier` (Claude Sonnet) protected by a forbidden-phrase guardrail, a `ReportBuilder`, and a pluggable `Notifier` layer (Discord webhook + Telegram bot). State is avoided by querying DART with a fixed time window. GitHub Actions cron drives the run; a thin FastAPI app exposes manual-trigger / latest-report / health endpoints.

**Tech Stack:** Python 3.11, httpx, pydantic v2 + pydantic-settings, anthropic SDK, PyYAML, FastAPI + uvicorn, pytest + respx, ruff.

---

## File Structure

```
StockBriefing-AI/
├── pyproject.toml                      # deps, pytest, ruff config
├── .env.example                        # documented secret names
├── watchlist.yaml                      # core watchlist (A feature)
├── reports/.gitkeep                    # local report archive (gitignored)
├── .github/workflows/daily-briefing.yml
├── src/stockbriefing/
│   ├── __init__.py
│   ├── config.py                       # Settings (env loading)
│   ├── models.py                       # Disclosure, NewsItem, MarketIndicator, ClassifiedItem, Report
│   ├── watchlist.py                    # load_watchlist()
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── dart.py                     # DartClient.fetch_disclosures(window)
│   │   ├── news.py                     # NaverNewsClient.search(keyword)
│   │   └── market.py                   # MarketClient.fetch_indicators()
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── guardrails.py               # scrub_forbidden(text)
│   │   └── classifier.py               # ImportanceClassifier.classify(items)
│   ├── report/
│   │   ├── __init__.py
│   │   └── builder.py                  # ReportBuilder.build(...) -> Report
│   ├── notifiers/
│   │   ├── __init__.py
│   │   ├── base.py                     # Notifier protocol
│   │   ├── discord.py                  # DiscordNotifier
│   │   └── telegram.py                 # TelegramNotifier
│   ├── storage.py                      # StorageInterface + FileStorage
│   ├── orchestrator.py                 # BriefingOrchestrator.run()
│   ├── api.py                          # FastAPI app
│   └── __main__.py                     # CLI: python -m stockbriefing
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_models.py
    ├── test_watchlist.py
    ├── collectors/test_dart.py
    ├── collectors/test_news.py
    ├── collectors/test_market.py
    ├── analysis/test_guardrails.py
    ├── analysis/test_classifier.py
    ├── report/test_builder.py
    ├── notifiers/test_discord.py
    ├── notifiers/test_telegram.py
    ├── test_storage.py
    └── test_orchestrator.py
```

**Time window rule (stateless dedup):** each run computes `window = [previous_market_close, now]` where `previous_market_close` is the most recent weekday 15:30 KST strictly before `now`. DART is queried for that date range; this removes the need for a "seen disclosures" database.

---

## Phase 0 — Scaffolding

### Task 1: Project metadata & dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `src/stockbriefing/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "stockbriefing"
version = "0.1.0"
description = "Daily Korean market briefing — disclosure/news importance classification (not investment advice)"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "anthropic>=0.39",
    "PyYAML>=6.0",
    "fastapi>=0.110",
    "uvicorn>=0.29",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "respx>=0.21", "ruff>=0.4"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Create empty package marker**

`src/stockbriefing/__init__.py`:
```python
"""StockBriefing AI — daily market briefing pipeline."""
__version__ = "0.1.0"
```

- [ ] **Step 3: Create `tests/conftest.py` (sets env defaults so config import never fails in tests)**

```python
import os
import pytest

os.environ.setdefault("DART_API_KEY", "test-dart-key")
os.environ.setdefault("NAVER_CLIENT_ID", "test-naver-id")
os.environ.setdefault("NAVER_CLIENT_SECRET", "test-naver-secret")
os.environ.setdefault("ECOS_API_KEY", "test-ecos-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DISCORD_WEBHOOK_URL", "https://discord.test/webhook")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123456")


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

- [ ] **Step 4: Install deps**

Run: `python -m pip install -e ".[dev]"`
Expected: ends with `Successfully installed ... stockbriefing-0.1.0`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/stockbriefing/__init__.py tests/conftest.py
git commit -m "chore: scaffold project metadata and test config"
```

---

### Task 2: Settings / config

**Files:**
- Create: `src/stockbriefing/config.py`
- Create: `.env.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
from stockbriefing.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("DART_API_KEY", "abc")
    monkeypatch.setenv("NAVER_CLIENT_ID", "id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "secret")
    monkeypatch.setenv("ECOS_API_KEY", "ecos")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anth")
    s = Settings()
    assert s.dart_api_key == "abc"
    assert s.naver_client_id == "id"
    assert s.classifier_model.startswith("claude")


def test_enabled_notifiers_reflects_present_secrets(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://x")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    s = Settings()
    assert "discord" in s.enabled_notifiers
    assert "telegram" not in s.enabled_notifiers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: stockbriefing.config`

- [ ] **Step 3: Write `src/stockbriefing/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    dart_api_key: str = ""
    naver_client_id: str = ""
    naver_client_secret: str = ""
    ecos_api_key: str = ""
    anthropic_api_key: str = ""

    discord_webhook_url: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    classifier_model: str = "claude-sonnet-4-6"
    summary_model: str = "claude-haiku-4-5-20251001"

    max_items_per_section: int = 15
    request_timeout_seconds: float = 20.0

    @property
    def enabled_notifiers(self) -> list[str]:
        names = []
        if self.discord_webhook_url:
            names.append("discord")
        if self.telegram_bot_token and self.telegram_chat_id:
            names.append("telegram")
        return names
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Write `.env.example`**

```
# DART OpenAPI (https://opendart.fss.or.kr/)
DART_API_KEY=

# Naver Search API (https://developers.naver.com/)
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=

# Bank of Korea ECOS (https://ecos.bok.or.kr/api/)
ECOS_API_KEY=

# Claude API (https://console.anthropic.com/)
ANTHROPIC_API_KEY=

# Notifiers
DISCORD_WEBHOOK_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

- [ ] **Step 6: Commit**

```bash
git add src/stockbriefing/config.py tests/test_config.py .env.example
git commit -m "feat: add settings and env example"
```

---

### Task 3: Domain models

**Files:**
- Create: `src/stockbriefing/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

`tests/test_models.py`:
```python
from datetime import datetime
from stockbriefing.models import (
    Disclosure, NewsItem, MarketIndicator, ClassifiedItem, Report, Importance
)


def test_disclosure_source_url_built_from_rcept_no():
    d = Disclosure(
        corp_name="삼성전자", stock_code="005930", report_name="단일판매ㆍ공급계약체결",
        rcept_no="20260530000123", rcept_dt="20260530", flr_nm="삼성전자",
    )
    assert d.source_url == "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260530000123"


def test_classified_item_carries_importance_and_reason():
    d = Disclosure(corp_name="A", stock_code="000001", report_name="유상증자결정",
                   rcept_no="1", rcept_dt="20260530", flr_nm="A")
    c = ClassifiedItem(kind="disclosure", importance=Importance.HIGH,
                       reason="자금조달 규모가 시총 대비 큼", title=d.report_name,
                       corp_name=d.corp_name, stock_code=d.stock_code, source_url=d.source_url)
    assert c.importance == Importance.HIGH


def test_report_renders_disclaimer_always():
    r = Report(generated_at=datetime(2026, 5, 30, 8, 0),
               indicators=[MarketIndicator(name="코스피", value="2650")],
               high=[], medium=[], watchlist=[])
    text = r.to_markdown()
    assert "투자 자문" in text and "추천이 아닙니다" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: stockbriefing.models`

- [ ] **Step 3: Write `src/stockbriefing/models.py`**

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, computed_field

DISCLAIMER = (
    "⚠️ 본 리포트는 공개된 공시·뉴스를 정리·분류한 정보 제공 목적의 자료이며, "
    "투자 자문이나 매매 추천이 아닙니다. 투자 판단과 책임은 본인에게 있습니다."
)


class Importance(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Disclosure(BaseModel):
    corp_name: str
    stock_code: str
    report_name: str
    rcept_no: str
    rcept_dt: str
    flr_nm: str

    @computed_field
    @property
    def source_url(self) -> str:
        return f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={self.rcept_no}"


class NewsItem(BaseModel):
    title: str
    link: str
    description: str = ""
    pub_date: str = ""
    stock_code: str = ""
    corp_name: str = ""


class MarketIndicator(BaseModel):
    name: str
    value: str
    unit: str = ""


class ClassifiedItem(BaseModel):
    kind: str  # "disclosure" | "news"
    importance: Importance
    reason: str
    title: str
    corp_name: str = ""
    stock_code: str = ""
    source_url: str = ""


class Report(BaseModel):
    generated_at: datetime
    indicators: list[MarketIndicator]
    high: list[ClassifiedItem]
    medium: list[ClassifiedItem]
    watchlist: list[ClassifiedItem]

    def to_markdown(self) -> str:
        lines: list[str] = []
        d = self.generated_at
        lines.append(f"📊 **StockBriefing — {d:%Y.%m.%d} {d:%H:%M}**\n")

        lines.append("━━ 시장 분위기 ━━")
        if self.indicators:
            for ind in self.indicators:
                lines.append(f"• {ind.name} {ind.value}{(' ' + ind.unit) if ind.unit else ''}")
        else:
            lines.append("• (지표 수집 실패)")
        lines.append("")

        lines.append("━━ 🔴 중요도 높음 ━━")
        lines.extend(_render_items(self.high))
        lines.append("")

        lines.append("━━ 🟡 중요도 중간 ━━")
        lines.extend(_render_items(self.medium))
        lines.append("")

        lines.append("━━ ⭐ 내 관심종목 ━━")
        lines.extend(_render_items(self.watchlist))
        lines.append("")

        lines.append("──────────────────")
        lines.append(DISCLAIMER)
        return "\n".join(lines)


def _render_items(items: list[ClassifiedItem]) -> list[str]:
    if not items:
        return ["• 해당 없음"]
    out: list[str] = []
    for it in items:
        label = f"[{it.corp_name}] {it.title}" if it.corp_name else it.title
        out.append(f"• {label}")
        out.append(f"  └ {it.reason}")
        if it.source_url:
            out.append(f"  └ {it.source_url}")
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/models.py tests/test_models.py
git commit -m "feat: add domain models and report markdown rendering"
```

---

## Phase 1 — Collectors

### Task 4: Time window helper

**Files:**
- Modify: `src/stockbriefing/models.py` (append `previous_market_close`, `Window`)
- Test: `tests/test_models.py` (append)

- [ ] **Step 1: Add failing test to `tests/test_models.py`**

```python
from datetime import date
from stockbriefing.models import previous_market_close


def test_previous_market_close_on_friday_morning_is_thursday():
    now = datetime(2026, 5, 29, 8, 0)  # Friday
    assert previous_market_close(now) == datetime(2026, 5, 28, 15, 30)


def test_previous_market_close_on_monday_morning_is_friday():
    now = datetime(2026, 6, 1, 8, 0)  # Monday
    assert previous_market_close(now) == datetime(2026, 5, 29, 15, 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_previous_market_close_on_monday_morning_is_friday -v`
Expected: FAIL with `ImportError: cannot import name 'previous_market_close'`

- [ ] **Step 3: Append to `src/stockbriefing/models.py`**

```python
from datetime import timedelta


def previous_market_close(now: datetime) -> datetime:
    """Most recent weekday 15:30 strictly before `now`."""
    candidate = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if candidate >= now:
        candidate -= timedelta(days=1)
    while candidate.weekday() >= 5:  # 5=Sat, 6=Sun
        candidate -= timedelta(days=1)
    return candidate
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/models.py tests/test_models.py
git commit -m "feat: add previous_market_close window helper"
```

---

### Task 5: DART disclosure collector

**Files:**
- Create: `src/stockbriefing/collectors/__init__.py` (empty)
- Create: `src/stockbriefing/collectors/dart.py`
- Test: `tests/collectors/test_dart.py`

DART `list.json` returns JSON: `{"status":"000","list":[{"corp_name","stock_code","report_nm","rcept_no","rcept_dt","flr_nm",...}]}`. `status` `"013"` means "no data". We request `bgn_de`/`end_de` = window start/end date (YYYYMMDD), `page_count=100`.

- [ ] **Step 1: Write the failing test**

`tests/collectors/test_dart.py`:
```python
import httpx, respx
from datetime import datetime
from stockbriefing.collectors.dart import DartClient


@respx.mock
def test_fetch_disclosures_parses_list():
    payload = {"status": "000", "message": "정상", "list": [
        {"corp_name": "삼성전자", "stock_code": "005930",
         "report_nm": "단일판매ㆍ공급계약체결", "rcept_no": "20260530000123",
         "rcept_dt": "20260530", "flr_nm": "삼성전자"},
        {"corp_name": "비상장사", "stock_code": "",
         "report_nm": "기타", "rcept_no": "20260530000999",
         "rcept_dt": "20260530", "flr_nm": "비상장사"},
    ]}
    respx.get("https://opendart.fss.or.kr/api/list.json").mock(
        return_value=httpx.Response(200, json=payload))

    client = DartClient(api_key="k", timeout=5)
    out = client.fetch_disclosures(datetime(2026, 5, 29, 15, 30), datetime(2026, 5, 30, 8, 0))

    assert len(out) == 1  # listed-only (stock_code present) kept
    assert out[0].corp_name == "삼성전자"


@respx.mock
def test_fetch_disclosures_handles_no_data_status():
    respx.get("https://opendart.fss.or.kr/api/list.json").mock(
        return_value=httpx.Response(200, json={"status": "013", "message": "조회된 데이타가 없습니다."}))
    client = DartClient(api_key="k", timeout=5)
    assert client.fetch_disclosures(datetime(2026, 5, 29), datetime(2026, 5, 30)) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/collectors/test_dart.py -v`
Expected: FAIL with `ModuleNotFoundError: stockbriefing.collectors.dart`

- [ ] **Step 3: Write `src/stockbriefing/collectors/dart.py`**

```python
from __future__ import annotations
from datetime import datetime
import httpx
from stockbriefing.models import Disclosure

DART_LIST_URL = "https://opendart.fss.or.kr/api/list.json"


class DartClient:
    def __init__(self, api_key: str, timeout: float = 20.0):
        self._api_key = api_key
        self._timeout = timeout

    def fetch_disclosures(self, start: datetime, end: datetime) -> list[Disclosure]:
        params = {
            "crtfc_key": self._api_key,
            "bgn_de": start.strftime("%Y%m%d"),
            "end_de": end.strftime("%Y%m%d"),
            "page_count": "100",
            "page_no": "1",
        }
        resp = httpx.get(DART_LIST_URL, params=params, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "000":
            return []
        out: list[Disclosure] = []
        for row in data.get("list", []):
            if not row.get("stock_code"):  # listed companies only
                continue
            out.append(Disclosure(
                corp_name=row["corp_name"],
                stock_code=row["stock_code"],
                report_name=row["report_nm"],
                rcept_no=row["rcept_no"],
                rcept_dt=row["rcept_dt"],
                flr_nm=row.get("flr_nm", ""),
            ))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/collectors/test_dart.py -v`
Expected: PASS (2 passed). Add empty `src/stockbriefing/collectors/__init__.py` if import fails.

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/collectors/__init__.py src/stockbriefing/collectors/dart.py tests/collectors/test_dart.py
git commit -m "feat: add DART disclosure collector with listed-only filter"
```

---

### Task 6: Naver news collector

**Files:**
- Create: `src/stockbriefing/collectors/news.py`
- Test: `tests/collectors/test_news.py`

Naver news API: `GET https://openapi.naver.com/v1/search/news.json?query=...&display=5&sort=date` with headers `X-Naver-Client-Id`, `X-Naver-Client-Secret`. Returns `{"items":[{"title","link","description","pubDate"}]}` with HTML entities/`<b>` tags to strip.

- [ ] **Step 1: Write the failing test**

`tests/collectors/test_news.py`:
```python
import httpx, respx
from stockbriefing.collectors.news import NaverNewsClient, strip_tags


def test_strip_tags_removes_b_and_entities():
    assert strip_tags("삼성<b>전자</b> &amp; SK") == "삼성전자 & SK"


@respx.mock
def test_search_returns_news_items_with_stock_code():
    payload = {"items": [
        {"title": "삼성<b>전자</b> 신규 계약", "link": "https://n.news/1",
         "description": "공급 <b>계약</b>", "pubDate": "Sat, 30 May 2026 06:00:00 +0900"},
    ]}
    respx.get("https://openapi.naver.com/v1/search/news.json").mock(
        return_value=httpx.Response(200, json=payload))
    client = NaverNewsClient(client_id="i", client_secret="s", timeout=5)
    items = client.search("삼성전자", stock_code="005930", display=5)
    assert items[0].title == "삼성전자 신규 계약"
    assert items[0].stock_code == "005930"
    assert items[0].corp_name == "삼성전자"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/collectors/test_news.py -v`
Expected: FAIL with `ModuleNotFoundError: stockbriefing.collectors.news`

- [ ] **Step 3: Write `src/stockbriefing/collectors/news.py`**

```python
from __future__ import annotations
import html
import re
import httpx
from stockbriefing.models import NewsItem

NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"
_TAG_RE = re.compile(r"<[^>]+>")


def strip_tags(text: str) -> str:
    return html.unescape(_TAG_RE.sub("", text)).strip()


class NaverNewsClient:
    def __init__(self, client_id: str, client_secret: str, timeout: float = 20.0):
        self._headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
        self._timeout = timeout

    def search(self, keyword: str, stock_code: str = "", display: int = 5) -> list[NewsItem]:
        params = {"query": keyword, "display": str(display), "sort": "date"}
        resp = httpx.get(NAVER_NEWS_URL, params=params, headers=self._headers, timeout=self._timeout)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            NewsItem(
                title=strip_tags(it.get("title", "")),
                link=it.get("link", ""),
                description=strip_tags(it.get("description", "")),
                pub_date=it.get("pubDate", ""),
                stock_code=stock_code,
                corp_name=keyword,
            )
            for it in items
        ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/collectors/test_news.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/collectors/news.py tests/collectors/test_news.py
git commit -m "feat: add Naver news collector with tag stripping"
```

---

### Task 7: Market indicator collector

**Files:**
- Create: `src/stockbriefing/collectors/market.py`
- Test: `tests/collectors/test_market.py`

For MVP, fetch USD/KRW from ECOS `StatisticSearch` JSON. ECOS responses vary; parse defensively and return `[]` on failure so the report degrades gracefully. KOSPI/KOSDAQ/oil are stubbed as TODO-free optional entries: the collector returns whatever it can parse; missing values are simply omitted (report shows what exists). We implement the FX call concretely and keep index/oil as a documented extension returning nothing for now.

- [ ] **Step 1: Write the failing test**

`tests/collectors/test_market.py`:
```python
import httpx, respx
from stockbriefing.collectors.market import MarketClient


@respx.mock
def test_fetch_indicators_parses_usdkrw():
    payload = {"StatisticSearch": {"row": [
        {"TIME": "20260529", "DATA_VALUE": "1365.5", "ITEM_NAME1": "원/달러"}
    ]}}
    respx.get(url__regex=r"https://ecos\.bok\.or\.kr/api/StatisticSearch/.*").mock(
        return_value=httpx.Response(200, json=payload))
    client = MarketClient(ecos_api_key="k", timeout=5)
    inds = client.fetch_indicators()
    fx = [i for i in inds if i.name == "원/달러 환율"]
    assert fx and fx[0].value == "1365.5"


@respx.mock
def test_fetch_indicators_degrades_on_error():
    respx.get(url__regex=r"https://ecos\.bok\.or\.kr/api/.*").mock(
        return_value=httpx.Response(500))
    client = MarketClient(ecos_api_key="k", timeout=5)
    assert client.fetch_indicators() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/collectors/test_market.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/collectors/market.py`**

```python
from __future__ import annotations
import datetime as dt
import httpx
from stockbriefing.models import MarketIndicator

# ECOS USD/KRW daily exchange rate: stat code 731Y001, item 0000001
ECOS_FX_STAT = "731Y001"
ECOS_FX_ITEM = "0000001"


class MarketClient:
    def __init__(self, ecos_api_key: str, timeout: float = 20.0):
        self._key = ecos_api_key
        self._timeout = timeout

    def fetch_indicators(self) -> list[MarketIndicator]:
        out: list[MarketIndicator] = []
        fx = self._fetch_usdkrw()
        if fx is not None:
            out.append(fx)
        return out

    def _fetch_usdkrw(self) -> MarketIndicator | None:
        today = dt.date.today().strftime("%Y%m%d")
        start = (dt.date.today() - dt.timedelta(days=10)).strftime("%Y%m%d")
        url = (
            f"https://ecos.bok.or.kr/api/StatisticSearch/{self._key}/json/kr/1/10/"
            f"{ECOS_FX_STAT}/D/{start}/{today}/{ECOS_FX_ITEM}"
        )
        try:
            resp = httpx.get(url, timeout=self._timeout)
            resp.raise_for_status()
            rows = resp.json().get("StatisticSearch", {}).get("row", [])
            if not rows:
                return None
            latest = rows[-1]
            return MarketIndicator(name="원/달러 환율", value=str(latest["DATA_VALUE"]), unit="원")
        except (httpx.HTTPError, KeyError, ValueError):
            return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/collectors/test_market.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/collectors/market.py tests/collectors/test_market.py
git commit -m "feat: add ECOS market indicator collector with graceful degradation"
```

---

### Task 8: Watchlist loader

**Files:**
- Create: `watchlist.yaml`
- Create: `src/stockbriefing/watchlist.py`
- Test: `tests/test_watchlist.py`

- [ ] **Step 1: Write the failing test**

`tests/test_watchlist.py`:
```python
from stockbriefing.watchlist import load_watchlist


def test_load_watchlist_parses_entries(tmp_path):
    f = tmp_path / "wl.yaml"
    f.write_text("stocks:\n  - {code: '005930', name: 삼성전자}\n  - {code: '000660', name: SK하이닉스}\n",
                 encoding="utf-8")
    wl = load_watchlist(str(f))
    assert wl == [("005930", "삼성전자"), ("000660", "SK하이닉스")]


def test_load_watchlist_missing_file_returns_empty():
    assert load_watchlist("does/not/exist.yaml") == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_watchlist.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/watchlist.py`**

```python
from __future__ import annotations
import os
import yaml


def load_watchlist(path: str = "watchlist.yaml") -> list[tuple[str, str]]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return [(str(s["code"]), str(s["name"])) for s in data.get("stocks", [])]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_watchlist.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Write the real `watchlist.yaml`**

```yaml
# 코어 관심종목 (A 기능). 단타 후보가 아니라 "늘 지켜보는" 종목.
stocks:
  - {code: "005930", name: 삼성전자}
  - {code: "000660", name: SK하이닉스}
```

- [ ] **Step 6: Commit**

```bash
git add watchlist.yaml src/stockbriefing/watchlist.py tests/test_watchlist.py
git commit -m "feat: add watchlist loader and default config"
```

---

## Phase 2 — Analysis

### Task 9: Guardrail filter

**Files:**
- Create: `src/stockbriefing/analysis/__init__.py` (empty)
- Create: `src/stockbriefing/analysis/guardrails.py`
- Test: `tests/analysis/test_guardrails.py`

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_guardrails.py`:
```python
from stockbriefing.analysis.guardrails import scrub_forbidden, FORBIDDEN


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_guardrails.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/analysis/guardrails.py`**

```python
from __future__ import annotations
import re

FORBIDDEN = [
    "매수 추천", "매도 추천", "매수", "매도", "추천 종목", "추천합니다", "추천 드립니다",
    "목표가", "사세요", "파세요", "오를 것", "오를것", "상승할 것", "급등 예상",
    "단언", "확실히 오른", "보장",
]
_REPLACEMENT = "[표현 제거됨]"
_PATTERN = re.compile("|".join(re.escape(w) for w in sorted(FORBIDDEN, key=len, reverse=True)))


def scrub_forbidden(text: str) -> str:
    """Replace any recommendation/prediction phrasing with a neutral marker."""
    return _PATTERN.sub(_REPLACEMENT, text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/analysis/test_guardrails.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/analysis/__init__.py src/stockbriefing/analysis/guardrails.py tests/analysis/test_guardrails.py
git commit -m "feat: add forbidden-phrase guardrail filter"
```

---

### Task 10: Importance classifier (Claude)

**Files:**
- Create: `src/stockbriefing/analysis/classifier.py`
- Test: `tests/analysis/test_classifier.py`

The classifier takes disclosures, builds one batched prompt asking Claude to return JSON `[{rcept_no, importance, reason}]`, parses it, applies `scrub_forbidden` to each `reason`, and returns `ClassifiedItem`s. The Anthropic client is injected so tests use a fake.

- [ ] **Step 1: Write the failing test**

`tests/analysis/test_classifier.py`:
```python
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
    return Disclosure(corp_name="A", stock_code="000001", report_name=name,
                      rcept_no=rcept_no, rcept_dt="20260530", flr_nm="A")


def test_classify_maps_importance_and_scrubs_reason():
    fake_json = json.dumps([
        {"rcept_no": "1", "importance": "HIGH", "reason": "공급계약 규모 큼. 매수 추천."},
        {"rcept_no": "2", "importance": "LOW", "reason": "정기 보고서"},
    ])
    clf = ImportanceClassifier(client=_FakeAnthropic(fake_json), model="m")
    items = clf.classify([_disc("1", "공급계약"), _disc("2", "분기보고서")])
    by_imp = {i.importance: i for i in items}
    assert by_imp[Importance.HIGH].title == "공급계약"
    assert "매수 추천" not in by_imp[Importance.HIGH].reason  # guardrail applied


def test_classify_empty_input_returns_empty_without_calling_llm():
    clf = ImportanceClassifier(client=None, model="m")
    assert clf.classify([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_classifier.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/analysis/classifier.py`**

```python
from __future__ import annotations
import json
from stockbriefing.models import Disclosure, ClassifiedItem, Importance
from stockbriefing.analysis.guardrails import scrub_forbidden

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
        "각 원소는 {\"rcept_no\", \"importance\"(HIGH|MEDIUM|LOW), \"reason\"} 형식이다.\n"
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
            out.append(ClassifiedItem(
                kind="disclosure",
                importance=importance,
                reason=scrub_forbidden(str(v.get("reason", ""))),
                title=d.report_name,
                corp_name=d.corp_name,
                stock_code=d.stock_code,
                source_url=d.source_url,
            ))
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/analysis/test_classifier.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/analysis/classifier.py tests/analysis/test_classifier.py
git commit -m "feat: add Claude importance classifier with guardrailed reasons"
```

---

## Phase 3 — Report

### Task 11: Report builder

**Files:**
- Create: `src/stockbriefing/report/__init__.py` (empty)
- Create: `src/stockbriefing/report/builder.py`
- Test: `tests/report/test_builder.py`

ReportBuilder splits classified items into `high`, `medium`, and a `watchlist` view (items whose stock_code is in the watchlist), caps each section, and constructs a `Report`.

- [ ] **Step 1: Write the failing test**

`tests/report/test_builder.py`:
```python
from datetime import datetime
from stockbriefing.report.builder import ReportBuilder
from stockbriefing.models import ClassifiedItem, Importance, MarketIndicator


def _item(code, imp):
    return ClassifiedItem(kind="disclosure", importance=imp, reason="r",
                          title="t", corp_name="c", stock_code=code)


def test_build_splits_sections_and_watchlist():
    items = [_item("005930", Importance.HIGH), _item("111111", Importance.MEDIUM),
             _item("222222", Importance.LOW)]
    rb = ReportBuilder(watchlist_codes={"005930"}, max_items=10)
    report = rb.build(datetime(2026, 5, 30, 8, 0),
                      indicators=[MarketIndicator(name="코스피", value="2650")],
                      classified=items)
    assert len(report.high) == 1
    assert len(report.medium) == 1
    assert [i.stock_code for i in report.watchlist] == ["005930"]
    assert "투자 자문" in report.to_markdown()


def test_build_caps_section_size():
    items = [_item(f"{i:06d}", Importance.HIGH) for i in range(20)]
    rb = ReportBuilder(watchlist_codes=set(), max_items=5)
    report = rb.build(datetime(2026, 5, 30, 8, 0), indicators=[], classified=items)
    assert len(report.high) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/report/test_builder.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/report/builder.py`**

```python
from __future__ import annotations
from datetime import datetime
from stockbriefing.models import ClassifiedItem, Importance, MarketIndicator, Report


class ReportBuilder:
    def __init__(self, watchlist_codes: set[str], max_items: int = 15):
        self._watchlist = watchlist_codes
        self._max = max_items

    def build(self, generated_at: datetime, indicators: list[MarketIndicator],
              classified: list[ClassifiedItem]) -> Report:
        high = [c for c in classified if c.importance == Importance.HIGH][: self._max]
        medium = [c for c in classified if c.importance == Importance.MEDIUM][: self._max]
        watchlist = [c for c in classified if c.stock_code in self._watchlist][: self._max]
        return Report(generated_at=generated_at, indicators=indicators,
                      high=high, medium=medium, watchlist=watchlist)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/report/test_builder.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/report/__init__.py src/stockbriefing/report/builder.py tests/report/test_builder.py
git commit -m "feat: add report builder with section caps and watchlist view"
```

---

## Phase 4 — Notifiers

### Task 12: Notifier base protocol

**Files:**
- Create: `src/stockbriefing/notifiers/__init__.py` (empty)
- Create: `src/stockbriefing/notifiers/base.py`
- Test: covered via discord/telegram tests

- [ ] **Step 1: Write `src/stockbriefing/notifiers/base.py`**

```python
from __future__ import annotations
from typing import Protocol
from stockbriefing.models import Report


class Notifier(Protocol):
    name: str

    def send(self, report: Report) -> None:
        ...


def chunk_text(text: str, limit: int) -> list[str]:
    """Split text on line boundaries so each chunk stays under `limit` chars."""
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit and current:
            chunks.append(current)
            current = ""
        current += line + "\n"
    if current.strip():
        chunks.append(current)
    return chunks
```

- [ ] **Step 2: Add a quick test for chunk_text**

`tests/notifiers/test_base.py`:
```python
from stockbriefing.notifiers.base import chunk_text


def test_chunk_text_respects_limit():
    text = "\n".join(f"line{i}" for i in range(100))
    chunks = chunk_text(text, limit=50)
    assert all(len(c) <= 51 for c in chunks)
    assert "line0" in chunks[0]
```

- [ ] **Step 3: Run test**

Run: `pytest tests/notifiers/test_base.py -v`
Expected: PASS (1 passed)

- [ ] **Step 4: Commit**

```bash
git add src/stockbriefing/notifiers/__init__.py src/stockbriefing/notifiers/base.py tests/notifiers/test_base.py
git commit -m "feat: add notifier protocol and text chunking helper"
```

---

### Task 13: Discord notifier

**Files:**
- Create: `src/stockbriefing/notifiers/discord.py`
- Test: `tests/notifiers/test_discord.py`

Discord webhook: `POST <webhook_url>` JSON `{"content": "..."}`, 2000-char limit per message.

- [ ] **Step 1: Write the failing test**

`tests/notifiers/test_discord.py`:
```python
import httpx, respx
from datetime import datetime
from stockbriefing.notifiers.discord import DiscordNotifier
from stockbriefing.models import Report


@respx.mock
def test_discord_send_posts_content():
    route = respx.post("https://discord.test/webhook").mock(return_value=httpx.Response(204))
    report = Report(generated_at=datetime(2026, 5, 30, 8, 0), indicators=[], high=[], medium=[], watchlist=[])
    DiscordNotifier(webhook_url="https://discord.test/webhook").send(report)
    assert route.called
    body = route.calls[0].request.content.decode()
    assert "StockBriefing" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifiers/test_discord.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/notifiers/discord.py`**

```python
from __future__ import annotations
import httpx
from stockbriefing.models import Report
from stockbriefing.notifiers.base import chunk_text

DISCORD_LIMIT = 1900


class DiscordNotifier:
    name = "discord"

    def __init__(self, webhook_url: str, timeout: float = 20.0):
        self._url = webhook_url
        self._timeout = timeout

    def send(self, report: Report) -> None:
        for chunk in chunk_text(report.to_markdown(), DISCORD_LIMIT):
            resp = httpx.post(self._url, json={"content": chunk}, timeout=self._timeout)
            resp.raise_for_status()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/notifiers/test_discord.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/notifiers/discord.py tests/notifiers/test_discord.py
git commit -m "feat: add Discord webhook notifier"
```

---

### Task 14: Telegram notifier

**Files:**
- Create: `src/stockbriefing/notifiers/telegram.py`
- Test: `tests/notifiers/test_telegram.py`

Telegram: `POST https://api.telegram.org/bot<token>/sendMessage` JSON `{"chat_id","text"}`, 4096-char limit.

- [ ] **Step 1: Write the failing test**

`tests/notifiers/test_telegram.py`:
```python
import httpx, respx
from datetime import datetime
from stockbriefing.notifiers.telegram import TelegramNotifier
from stockbriefing.models import Report


@respx.mock
def test_telegram_send_posts_message():
    route = respx.post("https://api.telegram.org/botTOKEN/sendMessage").mock(
        return_value=httpx.Response(200, json={"ok": True}))
    report = Report(generated_at=datetime(2026, 5, 30, 8, 0), indicators=[], high=[], medium=[], watchlist=[])
    TelegramNotifier(bot_token="TOKEN", chat_id="42").send(report)
    assert route.called
    body = route.calls[0].request.content.decode()
    assert "42" in body and "StockBriefing" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/notifiers/test_telegram.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/notifiers/telegram.py`**

```python
from __future__ import annotations
import httpx
from stockbriefing.models import Report
from stockbriefing.notifiers.base import chunk_text

TELEGRAM_LIMIT = 4000


class TelegramNotifier:
    name = "telegram"

    def __init__(self, bot_token: str, chat_id: str, timeout: float = 20.0):
        self._url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        self._chat_id = chat_id
        self._timeout = timeout

    def send(self, report: Report) -> None:
        for chunk in chunk_text(report.to_markdown(), TELEGRAM_LIMIT):
            resp = httpx.post(self._url, json={"chat_id": self._chat_id, "text": chunk},
                              timeout=self._timeout)
            resp.raise_for_status()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/notifiers/test_telegram.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/notifiers/telegram.py tests/notifiers/test_telegram.py
git commit -m "feat: add Telegram bot notifier"
```

---

## Phase 5 — Orchestration

### Task 15: Storage interface

**Files:**
- Create: `src/stockbriefing/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write the failing test**

`tests/test_storage.py`:
```python
from datetime import datetime
from stockbriefing.storage import FileStorage
from stockbriefing.models import Report


def test_file_storage_writes_markdown(tmp_path):
    report = Report(generated_at=datetime(2026, 5, 30, 8, 0), indicators=[], high=[], medium=[], watchlist=[])
    store = FileStorage(directory=str(tmp_path))
    path = store.save(report)
    assert path.endswith("2026-05-30.md")
    assert "StockBriefing" in (tmp_path / "2026-05-30.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/storage.py`**

```python
from __future__ import annotations
import os
from typing import Protocol
from stockbriefing.models import Report


class StorageInterface(Protocol):
    def save(self, report: Report) -> str:
        ...


class FileStorage:
    def __init__(self, directory: str = "reports"):
        self._dir = directory

    def save(self, report: Report) -> str:
        os.makedirs(self._dir, exist_ok=True)
        path = os.path.join(self._dir, f"{report.generated_at:%Y-%m-%d}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())
        return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_storage.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/storage.py tests/test_storage.py
git commit -m "feat: add storage interface and file storage"
```

---

### Task 16: Orchestrator

**Files:**
- Create: `src/stockbriefing/orchestrator.py`
- Test: `tests/test_orchestrator.py`

The orchestrator wires collectors → classifier → builder → notifiers. All collaborators are injected so the test uses fakes (no network). Collector failures must not abort the run (graceful degradation), but notifier failures should be collected and surfaced.

- [ ] **Step 1: Write the failing test**

`tests/test_orchestrator.py`:
```python
from datetime import datetime
from stockbriefing.orchestrator import BriefingOrchestrator
from stockbriefing.models import Disclosure, ClassifiedItem, Importance, MarketIndicator, Report


class _DartStub:
    def fetch_disclosures(self, start, end):
        return [Disclosure(corp_name="A", stock_code="005930", report_name="공급계약",
                           rcept_no="1", rcept_dt="20260530", flr_nm="A")]


class _MarketStub:
    def fetch_indicators(self):
        return [MarketIndicator(name="코스피", value="2650")]


class _ClassifierStub:
    def classify(self, disclosures):
        return [ClassifiedItem(kind="disclosure", importance=Importance.HIGH, reason="r",
                               title="공급계약", corp_name="A", stock_code="005930")]


class _RecordingNotifier:
    name = "rec"
    def __init__(self):
        self.sent = []
    def send(self, report):
        self.sent.append(report)


def test_run_builds_and_sends_report():
    notifier = _RecordingNotifier()
    orch = BriefingOrchestrator(
        dart=_DartStub(), market=_MarketStub(), classifier=_ClassifierStub(),
        watchlist_codes={"005930"}, notifiers=[notifier], storage=None, max_items=15,
    )
    report = orch.run(now=datetime(2026, 5, 30, 8, 0))
    assert isinstance(report, Report)
    assert len(notifier.sent) == 1
    assert report.high[0].corp_name == "A"


def test_run_continues_when_collector_fails():
    class _BoomDart:
        def fetch_disclosures(self, start, end):
            raise RuntimeError("dart down")
    notifier = _RecordingNotifier()
    orch = BriefingOrchestrator(
        dart=_BoomDart(), market=_MarketStub(), classifier=_ClassifierStub(),
        watchlist_codes=set(), notifiers=[notifier], storage=None, max_items=15,
    )
    report = orch.run(now=datetime(2026, 5, 30, 8, 0))
    assert report.high == []  # no disclosures, but run completed
    assert len(notifier.sent) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_orchestrator.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/orchestrator.py`**

```python
from __future__ import annotations
import logging
from datetime import datetime
from stockbriefing.models import previous_market_close, Report
from stockbriefing.report.builder import ReportBuilder

log = logging.getLogger("stockbriefing")


class BriefingOrchestrator:
    def __init__(self, dart, market, classifier, watchlist_codes, notifiers,
                 storage=None, max_items: int = 15):
        self._dart = dart
        self._market = market
        self._classifier = classifier
        self._builder = ReportBuilder(watchlist_codes=set(watchlist_codes), max_items=max_items)
        self._notifiers = notifiers
        self._storage = storage

    def run(self, now: datetime | None = None) -> Report:
        now = now or datetime.now()
        start = previous_market_close(now)

        disclosures = self._safe(lambda: self._dart.fetch_disclosures(start, now), "dart", default=[])
        indicators = self._safe(self._market.fetch_indicators, "market", default=[])
        classified = self._safe(lambda: self._classifier.classify(disclosures), "classifier", default=[])

        report = self._builder.build(now, indicators=indicators, classified=classified)

        if self._storage is not None:
            self._safe(lambda: self._storage.save(report), "storage", default=None)

        for notifier in self._notifiers:
            try:
                notifier.send(report)
            except Exception:  # noqa: BLE001
                log.exception("notifier %s failed", getattr(notifier, "name", "?"))
        return report

    @staticmethod
    def _safe(fn, label, default):
        try:
            return fn()
        except Exception:  # noqa: BLE001
            log.exception("%s step failed", label)
            return default
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_orchestrator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add orchestrator wiring collectors, classifier, notifiers"
```

---

### Task 17: Composition root & CLI entrypoint

**Files:**
- Create: `src/stockbriefing/__main__.py`
- Test: manual smoke (no unit test; this is the wiring of real clients)

- [ ] **Step 1: Write `src/stockbriefing/__main__.py`**

```python
from __future__ import annotations
import logging
import sys
from anthropic import Anthropic
from stockbriefing.config import Settings
from stockbriefing.collectors.dart import DartClient
from stockbriefing.collectors.market import MarketClient
from stockbriefing.analysis.classifier import ImportanceClassifier
from stockbriefing.notifiers.discord import DiscordNotifier
from stockbriefing.notifiers.telegram import TelegramNotifier
from stockbriefing.storage import FileStorage
from stockbriefing.watchlist import load_watchlist
from stockbriefing.orchestrator import BriefingOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def build_orchestrator(settings: Settings) -> BriefingOrchestrator:
    watchlist = load_watchlist()
    notifiers = []
    if "discord" in settings.enabled_notifiers:
        notifiers.append(DiscordNotifier(settings.discord_webhook_url, settings.request_timeout_seconds))
    if "telegram" in settings.enabled_notifiers:
        notifiers.append(TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id,
                                          settings.request_timeout_seconds))
    return BriefingOrchestrator(
        dart=DartClient(settings.dart_api_key, settings.request_timeout_seconds),
        market=MarketClient(settings.ecos_api_key, settings.request_timeout_seconds),
        classifier=ImportanceClassifier(Anthropic(api_key=settings.anthropic_api_key),
                                        settings.classifier_model),
        watchlist_codes={code for code, _ in watchlist},
        notifiers=notifiers,
        storage=FileStorage(),
        max_items=settings.max_items_per_section,
    )


def main() -> int:
    settings = Settings()
    if not settings.enabled_notifiers:
        logging.warning("no notifiers configured; report will be generated but not sent")
    orchestrator = build_orchestrator(settings)
    report = orchestrator.run()
    logging.info("briefing complete: %d high, %d medium", len(report.high), len(report.medium))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Smoke test the wiring compiles (no network call)**

Run: `python -c "from stockbriefing.__main__ import build_orchestrator; print('ok')"`
Expected: prints `ok`

- [ ] **Step 3: Commit**

```bash
git add src/stockbriefing/__main__.py
git commit -m "feat: add composition root and CLI entrypoint"
```

---

## Phase 6 — API & Automation

### Task 18: Thin FastAPI layer

**Files:**
- Create: `src/stockbriefing/api.py`
- Test: `tests/test_api.py`

Endpoints: `GET /health` → `{"status":"ok"}`; `GET /reports/latest` → latest markdown from `reports/`; `POST /run` → triggers orchestrator (injected, so test uses fake).

- [ ] **Step 1: Write the failing test**

`tests/test_api.py`:
```python
from fastapi.testclient import TestClient
from stockbriefing.api import create_app
from datetime import datetime
from stockbriefing.models import Report


class _Orch:
    def run(self, now=None):
        return Report(generated_at=datetime(2026, 5, 30, 8, 0), indicators=[], high=[], medium=[], watchlist=[])


def test_health_ok():
    app = create_app(orchestrator_factory=lambda: _Orch(), reports_dir="reports")
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}


def test_run_triggers_orchestrator():
    app = create_app(orchestrator_factory=lambda: _Orch(), reports_dir="reports")
    client = TestClient(app)
    resp = client.post("/run")
    assert resp.status_code == 200
    assert resp.json()["high"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write `src/stockbriefing/api.py`**

```python
from __future__ import annotations
import glob
import os
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse


def create_app(orchestrator_factory, reports_dir: str = "reports") -> FastAPI:
    app = FastAPI(title="StockBriefing AI")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/reports/latest", response_class=PlainTextResponse)
    def latest():
        files = sorted(glob.glob(os.path.join(reports_dir, "*.md")))
        if not files:
            return PlainTextResponse("no reports yet", status_code=404)
        with open(files[-1], encoding="utf-8") as f:
            return f.read()

    @app.post("/run")
    def run():
        report = orchestrator_factory().run()
        return {"high": len(report.high), "medium": len(report.medium),
                "watchlist": len(report.watchlist)}

    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/stockbriefing/api.py tests/test_api.py
git commit -m "feat: add thin FastAPI layer (health, latest report, manual run)"
```

---

### Task 19: GitHub Actions schedule

**Files:**
- Create: `.github/workflows/daily-briefing.yml`
- Create: `reports/.gitkeep`

- [ ] **Step 1: Write `.github/workflows/daily-briefing.yml`**

```yaml
name: daily-briefing

on:
  schedule:
    - cron: "0 23 * * 0-4"   # 23:00 UTC = 08:00 KST, Mon-Fri (Sun-Thu UTC)
  workflow_dispatch:

jobs:
  briefing:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e .
      - name: Run briefing
        env:
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
          NAVER_CLIENT_ID: ${{ secrets.NAVER_CLIENT_ID }}
          NAVER_CLIENT_SECRET: ${{ secrets.NAVER_CLIENT_SECRET }}
          ECOS_API_KEY: ${{ secrets.ECOS_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m stockbriefing
```

- [ ] **Step 2: Create `reports/.gitkeep`** (empty file)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/daily-briefing.yml reports/.gitkeep
git commit -m "ci: add daily 08:00 KST GitHub Actions schedule"
```

---

### Task 20: README & final verification

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# StockBriefing AI

매일 아침 8시(KST), 밤사이 시장 공시·뉴스를 수집해 **시장 영향도(중요도)를 분류**하고
디스코드·텔레그램으로 요약 리포트를 보내는 투자 의사결정 보조 도구.

> ⚠️ 본 프로젝트는 정보 정리·분류 도구이며, 투자 자문이나 매매 추천이 아닙니다.

## 아키텍처
DART/Naver/ECOS 수집 → Claude 중요도 분류(가드레일) → 리포트 생성 → Discord/Telegram 발송.
GitHub Actions cron으로 매 평일 08:00 KST 자동 실행 (무상태, 시간창 기반).

## 로컬 실행
```bash
python -m pip install -e ".[dev]"
cp .env.example .env   # 키 입력
pytest                 # 전체 테스트
python -m stockbriefing # 1회 브리핑 실행
uvicorn stockbriefing.api:create_app --factory  # API (선택)
```

## 설정
- `watchlist.yaml` — 코어 관심종목
- GitHub Secrets — 운영 키 (Settings → Secrets and variables → Actions)
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: all tests PASS (collect all suites green)

- [ ] **Step 3: Lint**

Run: `ruff check src tests`
Expected: `All checks passed!` (fix any reported issues)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add README with architecture and run instructions"
```

- [ ] **Step 5: Push**

```bash
git push -u origin main
```

---

## Self-Review (plan author)

**Spec coverage:**
- §2 B feature (market catalyst radar) → Task 5 (DART window scan) + Task 10 (classifier) + Task 11 (high/medium sections). ✅
- §2 A feature (core watchlist) → Task 8 (watchlist) + Task 11 (watchlist view). ✅
- §2 market indicators → Task 7 (ECOS FX; indices/oil documented as graceful-empty extension). ✅
- §2 8AM dual-channel send → Task 13/14 notifiers + Task 19 cron (23:00 UTC). ✅
- §3 guardrails (forbidden words, disclaimer, source links, classify-info-not-stocks) → Task 9 (scrub) + Task 10 (system prompt + scrub) + Task 3 (disclaimer + source_url). ✅
- §5 component boundaries → one file per component, injected collaborators. ✅
- §6 stateless / time-window → Task 4 (previous_market_close) + Task 16 (no persistence required). ✅
- §8 Sonnet/Haiku + FastAPI thin layer → config models + Task 18. ✅ (Haiku summary_model defined in config; reserved for future per-item summary — not required for MVP path.)
- §11 graceful degradation → Task 7 + Task 16 `_safe`. ✅

**Known intentional scope cuts (per design Out-of-Scope):** KIS price data, Postgres persistence (StorageInterface present, FileStorage only), US market section, news-item classification (only disclosures are classified in MVP; news is collected infra in Task 6 and wired for future enrichment — orchestrator MVP path classifies disclosures). News enrichment into the report is a fast-follow; the collector exists and is tested.

**Placeholder scan:** No TBD/TODO in code steps; every code step contains full code. ✅

**Type consistency:** `ClassifiedItem`, `Disclosure`, `Report`, `previous_market_close`, `scrub_forbidden`, `ReportBuilder.build`, `Notifier.send` signatures match across tasks. ✅

---

## Execution Handoff

After all tasks complete: full `pytest` green, `ruff` clean, then push to `origin main`. GitHub Secrets must be added in the repo before the first scheduled run.
