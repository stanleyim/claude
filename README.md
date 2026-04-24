# claude
주식 분석
# 📈 AI 주식 레이더 — 매일 TOP 10 자동 예측

> FDR + KRX API + Claude AI 기반 5팩터 복합 분석 시스템

---

## 🚀 GitHub 배포 순서 (핸드폰으로 완결)

### 1단계 — 저장소 만들기
1. GitHub 앱 실행 → **New repository**
2. Repository name: `claude`
3. Public 선택 → **Create repository**

### 2단계 — 파일 업로드
모든 파일을 다음 구조로 업로드:

```
ai-stock-radar/
├── index.html          ← 메인 대시보드 (이게 전부!)
├── scripts/
│   └── fetch_daily_data.py
├── .github/
│   └── workflows/
│       └── daily-update.yml
└── data/               ← GitHub Actions가 자동 생성
```

### 3단계 — GitHub Pages 활성화
1. Repository → **Settings**
2. Pages → Source: **Deploy from a branch**
3. Branch: `main` / `/ (root)` → **Save**
4. 잠시 후 `https://[유저명].github.io/ai-stock-radar` 접속

### 4단계 — KRX API Key 등록 (선택)
1. Settings → **Secrets and variables** → Actions
2. **New repository secret**
3. Name: `KRX_API_KEY` / Value: 발급받은 키 입력

### 5단계 — GitHub Actions 활성화
1. Repository → **Actions** 탭
2. `Daily Stock Analysis` workflow → **Enable**
3. **Run workflow** 버튼으로 수동 첫 실행 테스트

---

## 🧠 AI 스코어링 로직 (5팩터)

| 팩터 | 가중치 | 핵심 지표 |
|------|--------|-----------|
| 수급 | 30% | 외인/기관 연속 순매수일, 동반 매수 여부 |
| 모멘텀 | 25% | MA 정배열, RSI 50~70, MACD 골든크로스 |
| 재무 | 20% | PER(저평가), ROE(수익성), 부채비율(안정성) |
| 변동성 | 15% | 볼린저밴드 하단 반등, ATR 리스크 필터 |
| 거래량 | 10% | 20일 평균 대비 거래량 급증 |

**최종 선정 기준: 종합 점수 50점 이상 종목 중 상위 10개**

---

## 📅 자동 업데이트 스케줄

- GitHub Actions가 **매일 오전 8시 (한국시간)** 자동 실행
- 실제 FDR 데이터 수집 → 스코어 산출 → AI 코멘트 생성
- 대시보드 자동 반영

---

## 💡 단계별 업그레이드 로드맵

### v1.0 (현재) — Mock 데이터
- [x] 5팩터 스코어링 엔진
- [x] TOP 10 대시보드
- [x] Claude AI 코멘트
- [x] 종목 상세 차트

### v1.5 — 실제 데이터 연동
- [ ] FDR 실제 OHLCV 연동
- [ ] KRX API 수급 데이터 연동
- [ ] 매일 자동 업데이트

### v2.0 — 백테스트 & 검증
- [ ] 과거 추천 → 실제 등락률 추적
- [ ] 적중률 통계 대시보드
- [ ] 팩터별 기여도 분석

### v3.0 — 상업화 준비
- [ ] 로그인 / 회원 시스템
- [ ] 유료 구독 (월정액)
- [ ] 카카오톡 알림 연동
- [ ] 포트폴리오 관리 기능

---

## ⚠️ 투자 유의사항

이 서비스는 **참고 정보 제공** 목적으로만 사용하세요.
AI 분석 결과가 실제 수익을 보장하지 않으며,
모든 투자 결정과 그 결과는 본인의 책임입니다.

---

*Built with ❤️ using FDR + KRX API + Claude AI*
