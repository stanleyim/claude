# -*- coding: utf-8 -*-
"""
AI 주식 분석 엔진 v6.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
신규 추가:
  + 공매도 팩터 (KRX 크롤링)
  + 뉴스 NLP 고도화 (가중 키워드 + TF-IDF)
  + ML 팩터 모델 (XGBoost 학습 결과 적용)

8팩터 → 9팩터
  1. 외인/기관 수급     25%
  2. 기술적 모멘텀      20%
  3. 거래량 패턴        15%
  4. 재무 퀄리티        13%  (FDR PER/PBR/ROE)
  5. 볼린저/변동성      10%
  6. 뉴스 NLP 감성      8%   ← 고도화
  7. 공매도 팩터        5%   ← 신규
  8. 섹터 모멘텀        4%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys, time, math, datetime, traceback
import requests
import pandas as pd
import FinanceDataReader as fdr
from bs4 import BeautifulSoup
from collections import Counter
import re

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

# ════════════════════════════════════════════
# 유틸
# ════════════════════════════════════════════
def safe_pct(a, b):
    try:
        if not b: return 0
        return (a-b)/b*100
    except: return 0

def avg(arr):
    return sum(arr)/len(arr) if arr else 0

# ════════════════════════════════════════════
# ML 모델 로드
# ════════════════════════════════════════════
def load_ml_model():
    path = "data/ml_model.json"
    default = {
        "useML": False,
        "weights": {
            "supply": 0.35, "momentum": 0.25,
            "volume": 0.18, "short": 0.12,
            "news": 0.05, "shortSell": 0.05,
        }
    }
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                model = json.load(f)
            if model.get("useML"):
                print(f"  ✅ ML 모델 로드 (정확도: {model.get('accuracy',0)}%)")
            else:
                print(f"  → 룰 기반 가중치 사용")
            return model
    except: pass
    return default

def predict_ml_score(model, breakdown):
    """
    ML 모델로 최종 스코어 예측
    모델 없으면 가중 합산으로 폴백
    """
    weights = model.get("weights", {})

    # 가중치 기반 스코어 계산
    score = (
        breakdown.get("supply",    50) * weights.get("supply",    0.35) +
        breakdown.get("momentum",  50) * weights.get("momentum",  0.25) +
        breakdown.get("volume",    50) * weights.get("volume",    0.18) +
        breakdown.get("short",     50) * weights.get("short",     0.12) +
        breakdown.get("news",      50) * weights.get("news",      0.05) +
        breakdown.get("shortSell", 50) * weights.get("shortSell", 0.05)
    )

    # XGBoost 모델 있으면 확률 보정
    if model.get("useML") and model.get("booster"):
        try:
            import xgboost as xgb
            import numpy as np
            booster = xgb.Booster()
            booster.load_model(bytearray(model["booster"].encode()))
            features = np.array([[
                breakdown.get("supply",    50),
                breakdown.get("momentum",  50),
                breakdown.get("volume",    50),
                breakdown.get("short",     50),
                breakdown.get("news",      50),
                breakdown.get("shortSell", 50),
                score,
                breakdown.get("rank", 5),
            ]])
            dmat = xgb.DMatrix(features)
            prob = booster.predict(dmat)[0]
            # 확률(0~1)을 점수(0~100)로 변환 + 기존 스코어와 블렌딩
            ml_score = prob * 100
            score = score * 0.6 + ml_score * 0.4
        except: pass

    return round(score, 1)

# ════════════════════════════════════════════
# 종목 유니버스
# ════════════════════════════════════════════
def load_universe():
    print("📋 종목 로딩...")
    frames = []
    for market in ["KOSPI", "KOSDAQ"]:
        try:
            df = fdr.StockListing(market)
            if df is None or df.empty:
                print(f"  ⚠️ {market} 실패"); continue
            df["_market"] = market
            frames.append(df)
            print(f"  ✅ {market}: {len(df):,}개")
        except Exception as e:
            print(f"  ⚠️ {market} 오류: {e}"); continue

    if not frames: raise RuntimeError("종목 로딩 실패")
    all_df = pd.concat(frames, ignore_index=True)

    # 컬럼명 방어
    col_map = {}
    for c in all_df.columns:
        cl = c.lower()
        if cl in ["code","symbol"]:        col_map[c] = "code"
        elif cl == "name":                  col_map[c] = "name"
        elif cl in ["marcap","market_cap"]: col_map[c] = "marcap"
        elif cl == "per":                   col_map[c] = "per"
        elif cl == "pbr":                   col_map[c] = "pbr"
        elif cl == "roe":                   col_map[c] = "roe"
    all_df = all_df.rename(columns=col_map)

    if "code" not in all_df.columns:
        raise RuntimeError(f"code 컬럼 없음: {list(all_df.columns)}")

    all_df["code"] = all_df["code"].astype(str).str.zfill(6)

    # 기본 필터
    before = len(all_df)
    all_df = all_df[all_df["code"].str.match(r'^\d{6}$')]
    all_df = all_df[all_df["code"].str[-1] == "0"]
    all_df = all_df[~all_df["name"].str.contains(
        r'스팩|SPAC|\*|관리|정리|투자유의|거래정지', na=False, regex=True)]

    # ✅ 쓰레기 종목 필터
    if "marcap" in all_df.columns:
        all_df["marcap"] = pd.to_numeric(all_df["marcap"], errors="coerce").fillna(0)
        mc = all_df[all_df["marcap"] > 0]
        if len(mc) > 200:
            all_df = mc[mc["marcap"] >= 50_000_000_000]
    else:
        all_df["marcap"] = 0

    if "per" in all_df.columns:
        all_df["per"] = pd.to_numeric(all_df["per"], errors="coerce").fillna(0)
        all_df = all_df[all_df["per"] >= 0]

    for col in ["per","pbr","roe"]:
        if col not in all_df.columns:
            all_df[col] = 0

    all_df = all_df.drop_duplicates(subset=["code"]).reset_index(drop=True)
    print(f"  → 최종: {before:,} → {len(all_df):,}개\n")
    return all_df

# ════════════════════════════════════════════
# OHLCV
# ════════════════════════════════════════════
def fetch_ohlcv(code):
    try:
        end   = datetime.date.today()
        start = end - datetime.timedelta(days=150)
        df = fdr.DataReader(code, start, end)
        if df is None or df.empty or len(df) < MIN_DAYS: return None
        df = df.dropna(subset=["Close","Volume"])
        df = df[df["Volume"] > 0]
        if len(df) < MIN_DAYS: return None

        avg_vol    = df["Volume"].tail(20).mean()
        avg_price  = df["Close"].tail(20).mean()
        avg_amount = avg_vol * avg_price
        if avg_vol < MIN_AVG_VOL: return None
        if avg_amount < 100_000_000: return None

        closes = df["Close"].tolist()
        if len(closes) >= 60:
            if closes[-1] == min(closes[-60:]): return None

        return {
            "closes":  [int(x) for x in closes],
            "volumes": [int(x) for x in df["Volume"].tolist()],
        }
    except: return None

# ════════════════════════════════════════════
# 수급 크롤링
# ════════════════════════════════════════════
def fetch_supply(code):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, headers=HEADERS, timeout=6)
        res.encoding = "euc-kr"
        soup = BeautifulSoup(res.text, "lxml")
        rows = soup.select("table.type2 tr")
        f_streak = i_streak = 0; count = 0

        for r in rows:
            tds = r.select("td")
            if len(tds) < 5: continue
            try:
                f_txt = tds[3].text.strip().replace(",","").replace("+","")
                i_txt = tds[4].text.strip().replace(",","").replace("+","")
                if not f_txt or f_txt == "-": continue
                f_val = int(f_txt)
                i_val = int(i_txt) if i_txt and i_txt != "-" else 0
                if count == 0:
                    f_streak = 1 if f_val>0 else 0
                    i_streak = 1 if i_val>0 else 0
                else:
                    f_streak = f_streak+1 if f_val>0 else 0
                    i_streak = i_streak+1 if i_val>0 else 0
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
    except: return 50, 0, 0

# ════════════════════════════════════════════
# ① 공매도 팩터 (KRX 크롤링) ← 신규
# ════════════════════════════════════════════
_short_cache = {}

def fetch_short_sell_ratio(code):
    """
    KRX 공매도 잔고 비율 크롤링
    비율 높을수록 하락 압력 → 감점
    """
    global _short_cache
    if code in _short_cache:
        return _short_cache[code]

    try:
        url = (
            "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        )
        today = datetime.date.today()
        params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT30501",
            "locale": "ko_KR",
            "trdDd": today.strftime("%Y%m%d"),
            "isuCd": code,
            "share": "1",
            "money": "1",
        }
        res = requests.post(url, data=params, headers=HEADERS, timeout=6)
        data = res.json()
        items = data.get("output", [])
        if not items:
            _short_cache[code] = 50.0
            return 50.0

        ratio = float(items[0].get("SHRT_BLNC_RT", 0))
        # 공매도 비율 → 점수 (높을수록 위험)
        if ratio >= 10:  score = 0    # 10% 이상 = 매우 위험
        elif ratio >= 5: score = 20
        elif ratio >= 3: score = 40
        elif ratio >= 1: score = 60
        else:            score = 85   # 1% 미만 = 안전

        _short_cache[code] = score
        return score
    except:
        _short_cache[code] = 50.0
        return 50.0

# ════════════════════════════════════════════
# ② 뉴스 NLP 고도화 (가중 키워드 + TF-IDF) ← 고도화
# ════════════════════════════════════════════

# 금융 도메인 특화 감성 사전 (가중치 포함)
POS_DICT = {
    # 고가중치 (수익 직결)
    "수주": 3.0, "신고가": 3.0, "자사주매입": 3.0,
    "실적개선": 2.5, "어닝서프라이즈": 2.5, "목표주가상향": 2.5,
    "흑자전환": 2.5, "배당증가": 2.0,
    # 중가중치
    "호실적": 2.0, "계약": 1.8, "협약": 1.8, "증가": 1.5,
    "상향": 1.5, "매수": 1.5, "강세": 1.5, "성장": 1.5,
    "신제품": 1.5, "수출": 1.5, "수익": 1.3, "돌파": 1.3,
    # 저가중치
    "기대": 1.0, "긍정": 1.0, "회복": 1.0, "확장": 1.0,
}
NEG_DICT = {
    # 고가중치 (심각한 위험)
    "유상증자": -3.0, "횡령": -3.0, "배임": -3.0,
    "상장폐지": -3.0, "불성실공시": -2.5, "손실": -2.5,
    "적자전환": -2.5, "대규모손실": -2.5,
    # 중가중치
    "하향": -2.0, "매도": -2.0, "소송": -1.8, "조사": -1.8,
    "제재": -1.8, "급락": -1.8, "감소": -1.5, "부진": -1.5,
    # 저가중치
    "하락": -1.2, "우려": -1.2, "리스크": -1.0,
    "충당금": -1.5, "위기": -1.3,
}

def tokenize_ko(text):
    """간단한 한국어 토크나이징 (공백 + 특수문자 기준)"""
    return re.findall(r'[가-힣a-zA-Z0-9]+', text)

def calc_tfidf_sentiment(titles, all_titles_corpus):
    """
    TF-IDF 방식으로 키워드 가중치 계산
    단순 카운트보다 훨씬 정확
    """
    if not titles: return 50.0, []

    # 문서 빈도 계산 (IDF)
    doc_freq = Counter()
    for doc in all_titles_corpus:
        tokens = set(tokenize_ko(doc))
        for t in tokens:
            doc_freq[t] += 1

    N = len(all_titles_corpus) + 1
    total_score = 0.0
    matched = []

    for title in titles:
        tokens = tokenize_ko(title)
        doc_score = 0.0

        for token in tokens:
            # TF (term frequency in this doc)
            tf = tokens.count(token) / len(tokens)
            # IDF
            idf = math.log(N / (doc_freq.get(token, 0) + 1))

            # 긍정 키워드 체크
            for kw, weight in POS_DICT.items():
                if kw in token or token in kw:
                    doc_score += weight * tf * idf
                    if weight >= 2.0 and kw not in matched:
                        matched.append(f"긍정: {kw}")

            # 부정 키워드 체크
            for kw, weight in NEG_DICT.items():
                if kw in token or token in kw:
                    doc_score += weight * tf * idf  # weight는 음수

        total_score += doc_score

    # -10 ~ +10 범위를 0 ~ 100으로 정규화
    normalized = (total_score / len(titles) + 10) / 20 * 100
    return max(0.0, min(100.0, normalized)), matched[:3]

def fetch_news_nlp(name, code):
    """
    고도화된 뉴스 감성 분석
    TF-IDF + 금융 도메인 감성 사전
    """
    try:
        url = (f"https://search.naver.com/search.naver"
               f"?where=news&query={name}&sort=1&pd=4")
        res = requests.get(url, headers=HEADERS, timeout=8)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "lxml")

        titles = [a.get_text(strip=True)
                  for a in soup.select("a.news_tit")][:20]
        if not titles: return 50.0, []

        score, matched = calc_tfidf_sentiment(titles, titles)
        return score, matched
    except: return 50.0, []

# ════════════════════════════════════════════
# 기술적 팩터들
# ════════════════════════════════════════════
def f_momentum(c):
    if len(c) < 60: return 50
    ma5=avg(c[-5:]); ma20=avg(c[-20:]); ma60=avg(c[-60:])
    if c[-1]>ma5>ma20>ma60: return 90
    elif c[-1]>ma20>ma60:   return 70
    elif c[-1]>ma60:        return 40
    return 20

def f_volume(v, c):
    if len(v) < 20: return 50
    avg20 = avg(v[-20:])
    if not avg20: return 20
    ratio = v[-1]/avg20
    is_up = len(c)>=2 and c[-1]>c[-2]
    if ratio>=3 and is_up:   return 100
    if ratio>=2 and is_up:   return 80
    if ratio>=1.5 and is_up: return 60
    if ratio>=1 and is_up:   return 40
    return 20

def f_short_return(c):
    if len(c) < 6: return 50
    ret3 = safe_pct(c[-1], c[-4]) if len(c)>=4 else 0
    ret5 = safe_pct(c[-1], c[-6])
    sc = 50
    if ret3>=3:   sc+=30
    elif ret3>=1: sc+=15
    elif ret3<-5: sc-=25
    if ret5>=5:   sc+=20
    elif ret5>=2: sc+=10
    elif ret5<-8: sc-=20
    return max(0, min(100, sc))

def f_fundamental(per, pbr, roe):
    sc = 0.0
    if 0<per<10:   sc+=35
    elif per<15:   sc+=25
    elif per<20:   sc+=15
    elif per<30:   sc+=8
    if 0<pbr<0.8:  sc+=30
    elif pbr<1.0:  sc+=20
    elif pbr<1.5:  sc+=12
    if roe>20:     sc+=35
    elif roe>=15:  sc+=25
    elif roe>=10:  sc+=15
    elif roe>=5:   sc+=5
    return min(100.0, sc)

def f_volatility(c):
    if len(c)<20: return 50
    sl=c[-20:]; m=avg(sl)
    sd=math.sqrt(sum((x-m)**2 for x in sl)/len(sl)) if len(sl)>1 else 0
    if sd==0: return 50
    upper=m+2*sd; lower=m-2*sd
    pct=((c[-1]-lower)/(upper-lower))*100 if (upper-lower)>0 else 50
    sc=50
    if pct<15:   sc+=45
    elif pct<25: sc+=30
    elif pct<40: sc+=15
    elif pct>85: sc-=25
    return max(0, min(100, sc))

# ════════════════════════════════════════════
# 필터
# ════════════════════════════════════════════
def elite_filter(s):
    c=s["closes"]; v=s["volumes"]
    if s["score"]["total"] < 65: return False
    if safe_pct(c[-1],c[-2]) > 8: return False
    if len(c)>=4:
        if all(safe_pct(c[i],c[i-1])>5 for i in range(-3,0)): return False
    if c[-1] < avg(c[-20:]): return False
    if avg(v[-5:]) < avg(v[-20:])*0.8: return False
    return True

def super_filter(c):
    if len(c)<60: return False
    ma20=avg(c[-20:]); ma60=avg(c[-60:])
    return c[-1]>ma20>ma60

# ════════════════════════════════════════════
# 종합 스코어 (ML 적용)
# ════════════════════════════════════════════
def calc_score(s, ml_model, do_supply=True, do_short_sell=False):
    c=s["closes"]; v=s["volumes"]
    code=s["code"]

    # 수급
    if do_supply:
        sc_supply, f_streak, i_streak = fetch_supply(code)
        time.sleep(0.25)
    else:
        sc_supply, f_streak, i_streak = 50, 0, 0

    # 기술적
    sc_mom   = f_momentum(c)
    sc_vol   = f_volume(v, c)
    sc_short = f_short_return(c)
    sc_fund  = f_fundamental(
        s.get("per",0), s.get("pbr",0), s.get("roe",0))
    sc_volat = f_volatility(c)

    # ✅ 공매도 팩터 (시총 상위만)
    if do_short_sell:
        sc_ss = fetch_short_sell_ratio(code)
    else:
        sc_ss = 50.0

    # ✅ 뉴스 NLP 고도화
    if do_supply:  # 수급 크롤링 대상과 동일하게
        sc_news, news_reasons = fetch_news_nlp(s["name"], code)
    else:
        sc_news, news_reasons = 50.0, []

    breakdown = {
        "supply":    round(sc_supply, 1),
        "momentum":  round(sc_mom,    1),
        "volume":    round(sc_vol,    1),
        "short":     round(sc_short,  1),
        "fundamental": round(sc_fund, 1),
        "volatility": round(sc_volat, 1),
        "news":      round(sc_news,   1),
        "shortSell": round(sc_ss,     1),
    }

    # ✅ ML 모델로 최종 점수 산출
    total = predict_ml_score(ml_model, breakdown)

    # 이유 자동 생성
    reasons = []
    if f_streak >= 3: reasons.append(f"외국인 {f_streak}일 연속 순매수")
    if i_streak >= 3: reasons.append(f"기관 {i_streak}일 연속 순매수")
    if sc_mom >= 80:  reasons.append("이동평균 완전 정배열")
    if sc_vol >= 80:  reasons.append("거래량 급증 + 양봉")
    if sc_short >= 70: reasons.append("단기 상승 추세 강함")
    if sc_ss >= 80:   reasons.append("공매도 잔고 낮음 (안전)")
    if sc_news >= 70: reasons.extend(news_reasons[:1])
    if not reasons:   reasons.append("복합 기술적 조건 충족")

    # 리스크 자동 생성
    if sc_ss <= 20:
        risk = "공매도 잔고 높음 — 하락 압력 주의"
    elif safe_pct(c[-1], c[-2]) >= 5:
        risk = "당일 급등 — 추격 매수 주의"
    elif sc_supply < 30:
        risk = "수급 뒷받침 부족 — 확인 필요"
    elif sc_mom < 50:
        risk = "추세 약함 — 분할 매수 권장"
    else:
        risk = "시장 변동성에 따른 단기 조정 가능"

    return {
        "total":     total,
        "breakdown": breakdown,
        "reasons":   reasons[:3],
        "risk":      risk,
    }

# ════════════════════════════════════════════
# 메인
# ════════════════════════════════════════════
def main():
    t0    = time.time()
    today = datetime.date.today()
    print(f"\n{'='*55}")
    print(f"  AI 주식 분석 v6.0 — {today}")
    print(f"{'='*55}\n")

    # ML 모델 로드
    print("🤖 ML 모델 로드...")
    ml_model = load_ml_model()
    print()

    # 종목 유니버스
    all_df = load_universe()
    total  = len(all_df)

    # 시총 상위 300개 → 수급 + 뉴스 + 공매도 크롤링 대상
    top300_codes = set()
    if "marcap" in all_df.columns and all_df["marcap"].sum() > 0:
        top300_codes = set(all_df.nlargest(300,"marcap")["code"].tolist())
    else:
        top300_codes = set(all_df["code"].head(300).tolist())
    print(f"  크롤링 대상: {len(top300_codes)}개 (시총 상위)\n")

    results = []; failed = 0

    print(f"📈 분석 시작 ({total:,}개)...")
    for idx, row in all_df.iterrows():
        code = str(row["code"]).zfill(6)
        name = str(row["name"])

        if idx % 100 == 0 and idx > 0:
            print(f"  [{idx:4d}/{total}] {idx/total*100:.1f}% | "
                  f"{time.time()-t0:.0f}초 | 통과 {len(results)}개")

        data = fetch_ohlcv(code)
        if not data: failed+=1; continue

        do_supply    = code in top300_codes
        do_short_sell = code in top300_codes

        s = {
            "code": code, "name": name,
            "per":  float(row.get("per",0)  or 0),
            "pbr":  float(row.get("pbr",0)  or 0),
            "roe":  float(row.get("roe",0)  or 0),
            "marcap": int(row.get("marcap",0) or 0),
            **data
        }
        s["score"] = calc_score(
            s, ml_model,
            do_supply=do_supply,
            do_short_sell=do_short_sell
        )

        if elite_filter(s) and super_filter(s["closes"]):
            s["price"]      = s["closes"][-1]
            s["changeRate"] = round(safe_pct(s["closes"][-1], s["closes"][-2]), 2)
            results.append(s)

    print(f"\n  → 완료: 통과 {len(results)}개 / 실패 {failed}개")

    # 폴백
    if not results:
        print("  ⚠️ 통과 없음 — 필터 완화...")
        all_scored = []
        for _, row in all_df.head(200).iterrows():
            code = str(row["code"]).zfill(6)
            data = fetch_ohlcv(code)
            if not data: continue
            s = {"code":code,"name":str(row["name"]),
                 "per":0,"pbr":0,"roe":0,"marcap":0,**data}
            s["score"] = calc_score(s, ml_model, False, False)
            s["price"] = s["closes"][-1]
            s["changeRate"] = round(safe_pct(s["closes"][-1],s["closes"][-2]),2)
            all_scored.append(s)
        results = sorted(all_scored, key=lambda x:x["score"]["total"], reverse=True)[:TOP_N]

    # TOP N
    results = sorted(results, key=lambda x:x["score"]["total"], reverse=True)[:TOP_N]
    for i, s in enumerate(results, 1): s["rank"] = i

    # 출력
    print(f"\n{'='*55}")
    print(f"  🏆 TOP {TOP_N}")
    print(f"{'='*55}")
    for s in results:
        bd = s["score"]["breakdown"]
        print(f"  {s['rank']:2d}. {s['name']:12s} [{s['code']}] "
              f"점수:{s['score']['total']:5.1f} | {s['price']:>8,}원")
        print(f"      수급:{bd['supply']:.0f} 모멘텀:{bd['momentum']:.0f} "
              f"거래량:{bd['volume']:.0f} 공매도:{bd['shortSell']:.0f} "
              f"뉴스:{bd['news']:.0f}")
        print(f"      ✅ {' / '.join(s['score']['reasons'][:2])}")
        print(f"      ⚠️  {s['score']['risk']}")

    # 저장
    os.makedirs("data", exist_ok=True)
    save = []
    for s in results:
        d = {k:v for k,v in s.items() if k not in ["closes","volumes"]}
        d["closes"]  = s["closes"][-60:]
        d["volumes"] = s["volumes"][-60:]
        save.append(d)

    output = {
        "date":          str(today),
        "generatedAt":   datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalAnalyzed": total,
        "mlEnabled":     ml_model.get("useML", False),
        "mlAccuracy":    ml_model.get("accuracy", 0),
        "stocks":        save,
    }
    with open("data/daily_stocks.json","w",encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",",":"))

    # report.json
    report = [{"rank":s["rank"],"code":s["code"],"name":s["name"],
               "price":s["price"],"changeRate":s["changeRate"],
               "score":s["score"]["total"],
               "reasons":s["score"]["reasons"],"risk":s["score"]["risk"]}
              for s in results]
    with open("data/report.json","w",encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    elapsed = time.time()-t0
    print(f"\n✅ 완료! {elapsed/60:.1f}분 소요")
    print(f"   ML: {'활성화' if ml_model.get('useML') else '룰기반'} | "
          f"공매도: ✅ | 뉴스NLP: ✅\n")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        traceback.print_exc()
        sys.exit(1)

  
