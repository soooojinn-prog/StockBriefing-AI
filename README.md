# StockBriefing AI

매일 아침 7시(KST), 밤사이 시장 공시·뉴스를 수집해 **시장 영향도(중요도)를 분류**하고
디스코드·텔레그램으로 요약 리포트를 보내는 투자 의사결정 보조 도구.

> ⚠️ 본 프로젝트는 정보 정리·분류 도구이며, 투자 자문이나 매매 추천이 아닙니다.

## 아키텍처

```
DART/Naver/ECOS 수집 → Claude 중요도 분류(가드레일) → 리포트 생성 → Discord/Telegram 발송
```

- **무상태(stateless)** 설계: 매 실행마다 `[직전 장마감 ~ 현재]` 시간창으로 DART 공시를 조회 → 중복 제거용 DB 불필요
- **가드레일**: LLM은 종목이 아니라 *공시의 시장 영향도*만 HIGH/MEDIUM/LOW로 분류. 매수/매도/목표가 등 표현은 시스템이 차단
- **발송 추상화**: `Notifier` 인터페이스로 Discord/Telegram 동시 지원
- GitHub Actions cron으로 평일 07:00 KST(22:00 UTC) 자동 실행

## 로컬 실행

```bash
python -m pip install -e ".[dev]"
cp .env.example .env        # 키 입력
pytest                      # 전체 테스트
python -m stockbriefing     # 1회 브리핑 실행

# 선택: API 서버 (로컬 전용 권장: --host 127.0.0.1)
# /run, /reports/latest 는 API_TOKEN 설정 시에만 활성화되며 Bearer 토큰이 필요합니다.
uvicorn "stockbriefing.api:default_app" --factory --host 127.0.0.1
```

> 보안: `/run` 은 유료 LLM 호출과 발송을 유발하고 `/reports/latest` 는 리포트 내용을
> 노출하므로, 두 라우트는 `API_TOKEN` 공유 시크릿(`Authorization: Bearer <token>`)으로
> 보호됩니다. 토큰 미설정 시 두 라우트는 503으로 비활성화됩니다. `/health` 만 공개입니다.

## 설정

- `watchlist.yaml` — 코어 관심종목 (A 기능)
- 운영 키는 GitHub Secrets에 등록: repo Settings → Secrets and variables → Actions
  - `DART_API_KEY`, `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, `ECOS_API_KEY`,
    `ANTHROPIC_API_KEY`, `DISCORD_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`

## 데이터 소스

| 소스 | 용도 |
|---|---|
| DART OpenAPI | 전체 시장 공시 (촉매 핵심) |
| Naver 검색 API | 종목별 뉴스 보강 |
| 한국은행 ECOS | 원/달러 환율 등 거시지표 |

## 면책

본 시스템이 생성하는 리포트는 공개된 공시·뉴스를 정리·분류한 정보 제공 목적의 자료이며,
투자 자문이나 매매 추천이 아닙니다. 투자 판단과 책임은 사용자 본인에게 있습니다.
