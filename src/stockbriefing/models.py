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
                suffix = f" {ind.unit}" if ind.unit else ""
                lines.append(f"• {ind.name} {ind.value}{suffix}")
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


def previous_market_close(now: datetime) -> datetime:
    """Most recent weekday 15:30 strictly before ``now``."""
    candidate = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if candidate >= now:
        candidate -= timedelta(days=1)
    while candidate.weekday() >= 5:  # 5=Sat, 6=Sun
        candidate -= timedelta(days=1)
    return candidate
