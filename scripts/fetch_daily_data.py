# -*- coding: utf-8 -*-

import json, os, sys, time, math, datetime, traceback
import requests
import pandas as pd
import FinanceDataReader as fdr
from bs4 import BeautifulSoup

TOP_N       = 10
MIN_DAYS    = 60
MIN_AVG_VOL = 30000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ================= 유틸 =================

def safe_pct(a, b):
    try:
        if not b: return 0
        return (a - b) / b * 100
    except: return 0

def avg(arr):
    return sum(arr) / len(arr) if arr else 0

# ================= 종목 로딩 =================

def load_universe():
    print("📋 종목 로딩...")
    frames = []
    for market in ["KOSPI", "KOSDAQ"]:
        try:
            df = fdr.StockListing(market)
            if df is None or df.empty:
                print(f"  ⚠️ {market} 실패")
                continue
            df["_market"] = market
            frames.append(df)
            print(f"  ✅ {market}: {len(df):,}개")
        except Exception as e:
            print(f"  ⚠️ {market} 오류: {e}")
            continue

    if not frames:
        raise RuntimeError("종목 로딩 전체 실패")

    all_df = pd.concat(frames, ignore_index=True)

    # ✅ 컬럼명 방어 처리 (FDR 버전마다 다를 수 있음)
    col_map = {}
    for c in all_df.columns:
        cl = c.lower()
        if cl == "code" or cl == "symbol": col_map[c] = "code"
        elif cl == "name": col_map[c] = "name"
        elif cl == "marcap" or cl == "market_cap": col_map[c] = "marcap"

    all_df = all_df.rename(columns=col_map)

    if "code" not in all_df.columns:
        raise RuntimeError(f"code 컬럼 없음. 현재 컬럼: {list(all_df.columns)}")
    if "name" not in all_df.columns:
        raise RuntimeError(f"name 컬럼 없음. 현재 컬럼: {list(all_df.columns)}")

    # 기본 필터
    all_df["code"] = all_df["code"].astype(str).str.zfill(6)
    all_df = all_df[all_df["code"].str.match(r'^\d{6}$')]
    all_df = all_df[all_df["code"].str[-1] == "0"]  # 우선주 제외
    all_df = all_df[~all_df["name"].str.contains(
        r'스팩|SPAC|\*|관리|정리', na=False, regex=True)]
    all_df = all_df.drop_duplicates(subset=["code"]).reset_index(drop=True)

    # 시총 컬럼 정리
    if "marcap" in all_df.columns:
        all_df["marcap"] = pd.to_numeric(all_df["marcap"], errors="coerce").fillna(0)
    else:
        all_df["marcap"] = 0

    print(f"  → 최종: {len(all_df):,}개\n")
    return all_df

# ================= OHLCV =================

def fetch_ohlcv(code):
    try:
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=150)
        df = fdr.DataReader(code, start, end)

        if df is None or df.empty or len(df) < MIN_DAYS:
            return None

        df = df.dropna(subset=["Close", "Volume"])
        df = df[df["Volume"] > 0]

        if len(df) < MIN_DAYS:
            return None

        if df["Volume"].tail(20).mean() < MIN_AVG_VOL:
            return None

        return {
            "closes":  [int(x) for x in df["Close"].tolist()],
            "volumes": [int(x) for x in df["Volume"].tolist()],
        }
    except:
        return None

# ================= 수급 (시총 상위 300개만) =================

def fetch_supply(code):
    """
    ✅ 네이버 크롤링 과부하 방지
    → 시총 상위 300개만 실제 크롤링
    → 나머지는 기본값 반환
    """
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, headers=HEADERS, timeout=6)
        res.encoding = "euc-kr"
        soup = BeautifulSoup(res.text, "lxml")
        rows = soup.select("table.type2 tr")

        f_streak = i_streak = 0
        count = 0

        for r in rows:
            tds = r.select("td")
            if len(tds) < 5: continue
            try:
                f_txt = tds[3].text.strip().replace(",","").replace("+","")
                i_txt = tds[4].text.strip().replace(",","").replace("+","")
                if not f_txt or f_txt == "-": continue

                f_val = int(f_txt)
                i_val = int(i_txt) if i_txt and i_txt != "-" else 0

                # ✅ 연속 순매수만 — 끊기면 종료
                if count == 0:
                    f_streak = 1 if f_val > 0 else 0
                    i_streak = 1 if i_val > 0 else 0
                else:
                    f_streak = f_streak + 1 if f_val > 0 else 0
                    i_streak = i_streak + 1 if i_val > 0 else 0

                count += 1
                if count >= 10: break
            except: continue

        score = 0
        if f_streak >= 5: score += 55
        elif f_streak >= 3: score += 40
        elif f_streak >= 2: score += 25
        elif f_streak >= 1: score += 10

        if i_streak >= 4: score += 45
        elif i_streak >= 3: score += 30
        elif i_streak >= 2: score += 18
        elif i_streak >= 1: score += 8

        return min(100, score), f_streak, i_streak

    except:
        return 50, 0, 0

# ================= 팩터 =================

def f_momentum(c):
    if len(c) < 60: return 50
    ma5  = avg(c[-5:])
    ma20 = avg(c[-20:])
    ma60 = avg(c[-60:])
    if c[-1] > ma5 > ma20 > ma60: return 90
    elif c[-1] > ma20 > ma60:     return 70
    elif c[-1] > ma60:            return 40
    return 20

def f_volume(v):
    if len(v) < 20: return 50
    avg20 = avg(v[-20:])
    if avg20 == 0: return 20
    ratio = v[-1] / avg20
    if ratio >= 3:   return 100
    if ratio >= 2:   return 80
    if ratio >= 1.5: return 60
    if ratio >= 1:   return 40
    return 20

def f_short(c):
    if len(c) < 6: return 50
    ret3 = safe_pct(c[-1], c[-4]) if len(c) >= 4 else 0
    ret5 = safe_pct(c[-1], c[-6])
    score = 50
    if ret3 >= 3:   score += 30
    elif ret3 >= 1: score += 15
    elif ret3 < -5: score -= 25
    if ret5 >= 5:   score += 20
    elif ret5 >= 2: score += 10
    elif ret5 < -8: score -= 20
    return max(0, min(100, score))

# ================= 필터 =================

def elite_filter(s):
    c = s["closes"]
    v = s["volumes"]
    if s["score"]["total"] < 65: return False
    if safe_pct(c[-1], c[-2]) > 8: return False
    if len(c) >= 4:
        if all(safe_pct(c[i], c[i-1]) > 5 for i in range(-3, 0)):
            return False
    if c[-1] < avg(c[-20:]): return False
    if avg(v[-5:]) < avg(v[-20:]) * 0.8: return False
    return True

def super_filter(c):
    if len(c) < 60: return False
    ma20 = avg(c[-20:])
    ma60 = avg(c[-60:])
    if not (c[-1] > ma20 > ma60): return False
    return True

# ================= 스코어 =================

def calc_score(s, do_supply=True):
    c = s["closes"]
    v = s["volumes"]

    if do_supply:
        sc1, f_streak, i_streak = fetch_supply(s["code"])
        time.sleep(0.3)  # 네이버 크롤링 속도 제한
    else:
        sc1, f_streak, i_streak = 50, 0, 0

    sc2 = f_momentum(c)
    sc3 = f_volume(v)
    sc4 = f_short(c)

    total = (sc1 * 0.35 +
             sc2 * 0.30 +
             sc3 * 0.20 +
             sc4 * 0.15)

    # 이유 자동 생성
    reasons = []
    if f_streak >= 3: reasons.append(f"외국인 {f_streak}일 연속 순매수")
    if i_streak >= 3: reasons.append(f"기관 {i_streak}일 연속 순매수")
    if sc2 >= 80:     reasons.append("이동평균 완전 정배열")
    if sc3 >= 80:     reasons.append("거래량 급증 + 양봉")
    if sc4 >= 70:     reasons.append("단기 상승 추세 강함")
    if not reasons:   reasons.append("복합 기술적 조건 충족")

    # 리스크 자동 생성
    if safe_pct(c[-1], c[-2]) >= 5:
        risk = "당일 급등 — 추격 매수 주의"
    elif sc1 < 30:
        risk = "수급 뒷받침 부족 — 확인 필요"
    elif sc2 < 50:
        risk = "추세 약함 — 분할 매수 권장"
    else:
        risk = "시장 변동성에 따른 단기 조정 가능"

    return {
        "total": round(total, 1),
        "breakdown": {
            "supply":   round(sc1, 1),
            "momentum": round(sc2, 1),
            "volume":   round(sc3, 1),
            "short":    round(sc4, 1),
        },
        "reasons": reasons[:3],
        "risk":    risk,
    }

# ================= 리포트 =================

def generate_report(stocks):
    report = []
    for s in stocks:
        report.append({
            "rank":    s.get("rank", 0),
            "code":    s["code"],
            "name":    s["name"],
            "score":   s["score"]["total"],
            "reasons": s["score"]["reasons"],
            "risk":    s["score"]["risk"],
        })
    os.makedirs("data", exist_ok=True)
    with open("data/report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  → report.json 저장 ({len(report)}개)")

# ================= 메인 =================

def main():
    t0    = time.time()
    today = datetime.date.today()
    print(f"\n{'='*52}")
    print(f"  AI 주식 분석 시작 — {today}")
    print(f"{'='*52}\n")

    # 종목 유니버스 로딩
    all_df = load_universe()
    total  = len(all_df)

    # ✅ 시총 상위 300개만 수급 크롤링 대상으로 지정
    top300_codes = set()
    if "marcap" in all_df.columns:
        top300 = all_df.nlargest(300, "marcap")
        top300_codes = set(top300["code"].tolist())
    else:
        # marcap 없으면 앞 300개
        top300_codes = set(all_df["code"].head(300).tolist())

    print(f"  수급 크롤링 대상: {len(top300_codes)}개 (시총 상위)")

    results = []
    failed  = 0

    print(f"\n📈 분석 시작 ({total:,}개)...")
    for idx, row in all_df.iterrows():
        code = str(row["code"]).zfill(6)
        name = str(row["name"])

        if idx % 100 == 0 and idx > 0:
            print(f"  [{idx:4d}/{total}] {idx/total*100:.1f}% | "
                  f"{time.time()-t0:.0f}초 | 통과 {len(results)}개")

        # OHLCV
        data = fetch_ohlcv(code)
        if not data:
            failed += 1
            continue

        s = {"code": code, "name": name, **data}

        # ✅ 수급: 시총 상위 300개만 크롤링, 나머지 기본값
        do_supply = code in top300_codes
        s["score"] = calc_score(s, do_supply=do_supply)

        # 2단계 필터
        if elite_filter(s) and super_filter(s["closes"]):
            s["price"]      = s["closes"][-1]
            s["changeRate"] = round(safe_pct(s["closes"][-1], s["closes"][-2]), 2)
            results.append(s)

    print(f"\n  → 완료: 통과 {len(results)}개 / 실패 {failed}개")

    if not results:
        print("  ⚠️ 통과 종목 없음 — 필터 조건 완화 필요")
        # 필터 없이 점수 상위 10개라도 저장
        all_scored = []
        for idx, row in all_df.head(200).iterrows():
            code = str(row["code"]).zfill(6)
            data = fetch_ohlcv(code)
            if not data: continue
            s = {"code":code,"name":str(row["name"]),**data}
            s["score"] = calc_score(s, do_supply=False)
            s["price"] = s["closes"][-1]
            s["changeRate"] = round(safe_pct(s["closes"][-1],s["closes"][-2]),2)
            all_scored.append(s)
        results = sorted(all_scored, key=lambda x:x["score"]["total"], reverse=True)[:TOP_N]

    # TOP N
    results = sorted(results, key=lambda x: x["score"]["total"], reverse=True)[:TOP_N]
    for i, s in enumerate(results, 1):
        s["rank"] = i

    # 출력
    print(f"\n{'='*52}")
    print(f"  🏆 TOP {TOP_N}")
    print(f"{'='*52}")
    for s in results:
        print(f"  {s['rank']:2d}. {s['name']:12s} [{s['code']}] "
              f"점수:{s['score']['total']:5.1f} | {s['price']:>8,}원")
        print(f"      ✅ {' / '.join(s['score']['reasons'][:2])}")
        print(f"      ⚠️  {s['score']['risk']}")

    # 저장
    os.makedirs("data", exist_ok=True)
    save = []
    for s in results:
        d = {k: v for k, v in s.items() if k not in ["closes", "volumes"]}
        d["closes"]  = s["closes"][-60:]
        d["volumes"] = s["volumes"][-60:]
        save.append(d)

    output = {
        "date":          str(today),
        "generatedAt":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalAnalyzed": total,
        "stocks":        save,
    }
    with open("data/daily_stocks.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\n  → daily_stocks.json 저장 ({len(save)}개)")

    generate_report(results)

    print(f"\n✅ 완료! 소요시간: {(time.time()-t0)/60:.1f}분\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        traceback.print_exc()
        sys.exit(1)
        
