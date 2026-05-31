from __future__ import annotations

from datetime import datetime, timedelta
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
    summary: str = ""  # LLM one-line summary (optional)


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


class WatchlistEntry(BaseModel):
    """Independent per-stock view for a watchlist company: its disclosures and news."""

    name: str
    stock_code: str
    disclosures: list[Disclosure] = []
    news: list[NewsItem] = []


class Report(BaseModel):
    generated_at: datetime
    indicators: list[MarketIndicator]
    high: list[ClassifiedItem]
    # Theme views over all disclosures (keyword-based, DART-only):
    earnings: list[Disclosure] = []  # 실적·손익구조 변동 (흑자전환 포함)
    ownership: list[Disclosure] = []  # 대량보유·지분 변동 (수급 신호)
    # Watchlist is an INDEPENDENT view: each stock's disclosures + overnight news,
    # regardless of market-wide importance classification.
    watchlist: list[WatchlistEntry] = []

    def to_markdown(self) -> str:
        lines: list[str] = []
        d = self.generated_at
        lines.append(f"📊 **StockBriefing — {d:%Y.%m.%d} {d:%H:%M}**\n")

        lines.append("━━ 시장 분위기 ━━")
        if self.indicators:
            for ind in self.indicators:
                suffix = f" {ind.unit}" if ind.unit else ""
                lines.append(f"• {ind.name} {ind.value}{suffix}")
        else:
            lines.append("• (지표 수집 실패)")
        lines.append("")

        lines.append("━━ 🔴 중요도 높음 ━━")
        lines.extend(_render_items(self.high))
        lines.append("")

        lines.append("━━ 📈 실적·손익 공시 (흑자전환 등) ━━")
        lines.extend(_render_disclosures(self.earnings))
        lines.append("")

        lines.append("━━ 🏦 대량보유·지분 변동 (수급 신호) ━━")
        lines.extend(_render_disclosures(self.ownership))
        lines.append("")

        lines.append("━━ ⭐ 내 관심종목 ━━")
        lines.extend(_render_watchlist(self.watchlist))
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


def _render_disclosures(items: list[Disclosure]) -> list[str]:
    if not items:
        return ["• 해당 없음"]
    out: list[str] = []
    for d in items:
        out.append(f"• [{d.corp_name}] {d.report_name.strip()}")
        out.append(f"  └ {d.source_url}")
    return out


def _render_watchlist(entries: list[WatchlistEntry]) -> list[str]:
    if not entries:
        return ["• 해당 없음"]
    out: list[str] = []
    for e in entries:
        out.append(f"▸ {e.name}")
        for d in e.disclosures:
            out.append(f"  · [공시] {d.report_name.strip()}")
            out.append(f"    └ {d.source_url}")
        for n in e.news:
            out.append(f"  · [뉴스] {n.title}")
            if n.summary:
                out.append(f"    └ {n.summary}")
            out.append(f"    └ {n.link}")
        if not e.disclosures and not e.news:
            out.append("  · 새 소식 없음")
    return out


def previous_market_close(now: datetime) -> datetime:
    """Most recent weekday 15:30 strictly before ``now``."""
    candidate = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if candidate >= now:
        candidate -= timedelta(days=1)
    while candidate.weekday() >= 5:  # 5=Sat, 6=Sun
        candidate -= timedelta(days=1)
    return candidate
