# -*- coding: utf-8 -*-

import FinanceDataReader as fdr
import datetime, json, os, time, traceback

START_DATE = "2025-01-01"
END_DATE   = "2025-04-01"
TOP_N      = 5

# ================= 유틸 =================

def pct(a, b):
    return (a - b) / b * 100 if b != 0 else 0

def avg(arr):
    return sum(arr) / len(arr) if arr else 0

# ================= 데이터 =================

def load_all_prices(codes, start, end):
    """
    ✅ 종목당 딱 1번만 다운로드
    메모리에 캐시 → 날짜별 슬라이싱으로 처리
    → API 호출 횟수 대폭 감소
    """
    cache = {}
    total = len(codes)
    for i, code in enumerate(codes):
        if i % 20 == 0:
            print(f"  데이터 로딩: [{i}/{total}]")
        try:
            df = fdr.DataReader(code, start, end)
            if df is not None and len(df) >= 30:
                cache[code] = df
            time.sleep(0.05)  # 과부하 방지
        except:
            continue
    print(f"  → 로딩 완료: {len(cache)}개\n")
    return cache

# ================= 팩터 =================

def f_momentum(closes):
    if len(closes) < 20: return 0
    ma5  = avg(closes[-5:])
    ma20 = avg(closes[-20:])
    if closes[-1] > ma5 > ma20: return 100
    elif closes[-1] > ma20:     return 70
    return 40

def f_volume(volumes):
    if len(volumes) < 20: return 0
    avg20 = avg(volumes[-20:])
    if avg20 == 0: return 0
    ratio = volumes[-1] / avg20
    if ratio > 2:   return 100
    elif ratio > 1.5: return 70
    return 40

def f_short(closes):
    """단기 수익률 팩터 (3일/5일)"""
    if len(closes) < 6: return 50
    ret3 = pct(closes[-1], closes[-4]) if len(closes) >= 4 else 0
    ret5 = pct(closes[-1], closes[-6])
    score = 50
    if ret3 >= 3:   score += 30
    elif ret3 >= 1: score += 15
    elif ret3 < -5: score -= 25
    if ret5 >= 5:   score += 20
    elif ret5 >= 2: score += 10
    elif ret5 < -8: score -= 20
    return max(0, min(100, score))

# ================= 전략 =================

def calc_score(df_slice):
    closes  = df_slice["Close"].tolist()
    volumes = df_slice["Volume"].tolist()

    sc_mom = f_momentum(closes)
    sc_vol = f_volume(volumes)
    sc_sht = f_short(closes)

    # 가중치: 모멘텀 50% / 거래량 30% / 단기수익 20%
    total = sc_mom * 0.5 + sc_vol * 0.3 + sc_sht * 0.2
    return round(total, 1)

# ================= 백테스트 =================

def backtest():
    print("===== 백테스트 시작 =====")
    print(f"기간: {START_DATE} ~ {END_DATE}")
    print(f"TOP N: {TOP_N}\n")

    # 종목 리스트
    try:
        listing = fdr.StockListing("KOSPI")
        # ✅ 컬럼명 방어 처리
        code_col = None
        for c in listing.columns:
            if c.lower() in ["code", "symbol"]:
                code_col = c
                break
        if code_col is None:
            raise RuntimeError(f"code 컬럼 없음: {list(listing.columns)}")

        codes = listing[code_col].astype(str).str.zfill(6).head(100).tolist()
        print(f"분석 종목: {len(codes)}개")
    except Exception as e:
        print(f"종목 로딩 오류: {e}")
        traceback.print_exc()
        return

    # 시장 날짜 기준 (KOSPI 지수)
    try:
        ks11 = fdr.DataReader("KS11", START_DATE, END_DATE)
        date_range = ks11.index.tolist()
        print(f"거래일: {len(date_range)}일\n")
    except Exception as e:
        print(f"지수 로딩 오류: {e}")
        return

    # ✅ 전체 가격 데이터 1번만 다운로드
    print("📥 가격 데이터 로딩 중 (1회만)...")
    price_cache = load_all_prices(codes, START_DATE, END_DATE)

    # ================= 날짜별 백테스트 =================
    results      = []
    daily_detail = []

    print("📊 날짜별 시뮬레이션 시작...")
    for i in range(30, len(date_range) - 1):
        today    = date_range[i]
        next_day = date_range[i + 1]

        picks = []

        for code, df_full in price_cache.items():
            # ✅ 메모리 슬라이싱 — 추가 API 호출 없음
            df_today = df_full[df_full.index <= today]
            if len(df_today) < 30:
                continue

            sc = calc_score(df_today)
            if sc < 70:
                continue

            price_today = df_today["Close"].iloc[-1]

            # 다음날 가격 — 캐시에서 슬라이싱
            df_next = df_full[df_full.index <= next_day]
            if len(df_next) == 0:
                continue

            price_next = df_next["Close"].iloc[-1]
            ret = pct(price_next, price_today)

            picks.append({
                "code": code,
                "score": sc,
                "ret": ret,
            })

        if not picks:
            continue

        # 점수 상위 TOP N 선정
        picks = sorted(picks, key=lambda x: x["score"], reverse=True)[:TOP_N]
        avg_ret = avg([p["ret"] for p in picks])
        results.append(avg_ret)

        daily_detail.append({
            "date":    str(today.date()) if hasattr(today, 'date') else str(today),
            "picks":   [p["code"] for p in picks],
            "avg_ret": round(avg_ret, 2),
        })

    # ================= 결과 =================
    if not results:
        print("⚠️ 결과 없음 — 조건을 완화하거나 기간을 늘려주세요")
        return

    win       = len([x for x in results if x > 0])
    total     = len(results)
    hit_rate  = win / total * 100 if total else 0
    avg_ret   = avg(results)
    best_day  = max(results)
    worst_day = min(results)

    print("\n===== 백테스트 결과 =====")
    print(f"총 거래일:   {total}일")
    print(f"승률:        {round(hit_rate, 1)}%")
    print(f"평균 수익:   {round(avg_ret, 2)}%")
    print(f"최고 수익일: {round(best_day, 2)}%")
    print(f"최저 수익일: {round(worst_day, 2)}%")
    print("=========================\n")

    # 저장
    os.makedirs("data", exist_ok=True)
    output = {
        "period":     f"{START_DATE} ~ {END_DATE}",
        "top_n":      TOP_N,
        "total_days": total,
        "hit_rate":   round(hit_rate, 1),
        "avg_return": round(avg_ret, 2),
        "best_day":   round(best_day, 2),
        "worst_day":  round(worst_day, 2),
        "daily":      daily_detail[-30:],  # 최근 30일치만 저장
    }
    with open("data/backtest.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("✅ data/backtest.json 저장 완료")

# ================= 실행 =================

if __name__ == "__main__":
    try:
        backtest()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        traceback.print_exc()
  
