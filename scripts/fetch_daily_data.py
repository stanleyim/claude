"""
AI 주식 분석 엔진 v4.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v4 변경사항
  + 단기 수익률 팩터 (8번째 팩터, 4%)
  + AI 코멘트 JSON 구조화 (reasons + risk)
  + rank 필드 명시
  + 성과 추적 (history.json) 자동 업데이트
  + 누적 적중률 계산 및 저장

8팩터 가중치
  1. 외인/기관 수급     25%  ← 네이버금융 실제 크롤링
  2. 기술적 모멘텀      18%
  3. 거래량 패턴        15%
  4. 재무 퀄리티        13%
  5. 볼린저/변동성      10%
  6. 공시/뉴스 감성     10%
  7. 섹터 모멘텀         5%
  8. 단기 수익률         4%  ← 신규
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json, os, sys, time, math, datetime, traceback
import requests
import pandas as pd
import FinanceDataReader as fdr
from bs4 import BeautifulSoup

# ── 설정 ──────────────────────────────────────────────────
TOP_N        = 10
MIN_MARCAP   = 50_000_000_000
MIN_AVG_VOL  = 30_000
MIN_DAYS     = 40
OHLCV_PERIOD = 100
RETRY        = 3
RETRY_DELAY  = 2
DART_API_KEY = os.environ.get("DART_API_KEY", "")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── 유틸 ──────────────────────────────────────────────────
def safe_float(v, default=0.0):
    try:
        r = float(v)
        return default if (math.isnan(r) or math.isinf(r)) else r
    except: return default

def safe_int(v, default=0):
    try: return int(float(v))
    except: return default

def retry_call(func, *args, **kwargs):
    for i in range(RETRY):
        try: return func(*args, **kwargs)
        except Exception as e:
            print(f"    재시도 {i+1}/{RETRY}: {e}")
            if i < RETRY - 1: time.sleep(RETRY_DELAY)
    return None

def _avg(arr): return sum(arr)/len(arr) if arr else 0.0
def _std(arr):
    m = _avg(arr)
    return math.sqrt(sum((x-m)**2 for x in arr)/len(arr)) if len(arr)>1 else 0.0

# ══════════════════════════════════════════════════════════
# 1. 종목 유니버스
# ══════════════════════════════════════════════════════════
def load_universe():
    print("📋 KRX 전체 종목 로딩...")
    frames = []
    for market in ["KOSPI", "KOSDAQ"]:
        df = retry_call(fdr.StockListing, market)
        if df is None or df.empty:
            print(f"  ⚠️  {market} 실패"); continue
        df["Market"] = market
        frames.append(df)
        print(f"  ✅ {market}: {len(df):,}개")
    if not frames: raise RuntimeError("종목 로딩 실패")

    all_df = pd.concat(frames, ignore_index=True)
    rename = {"Code":"code","Name":"name","Market":"market",
               "Sector":"sector","Marcap":"marcap",
               "PER":"per","PBR":"pbr","ROE":"roe"}
    all_df.rename(columns={k:v for k,v in rename.items() if k in all_df.columns}, inplace=True)
    for c in ["sector","per","pbr","roe","marcap"]:
        if c not in all_df.columns: all_df[c] = 0

    before = len(all_df)
    all_df = all_df[all_df["code"].astype(str).str.match(r'^\d{6}$')]
    all_df = all_df[all_df["code"].astype(str).str[-1] == "0"]
    all_df = all_df[~all_df["name"].str.contains(
        r'스팩|SPAC|\*|관리|정리|투자유의|거래정지', na=False, regex=True)]
    all_df["marcap"] = pd.to_numeric(all_df["marcap"], errors="coerce").fillna(0)
    mc = all_df[all_df["marcap"] > 0]
    if len(mc) > 200: all_df = mc[mc["marcap"] >= MIN_MARCAP]
    all_df = all_df.drop_duplicates(subset=["code"]).reset_index(drop=True)

    print(f"  → 필터 후: {before:,} → {len(all_df):,}개\n")
    return all_df

# ══════════════════════════════════════════════════════════
# 2. OHLCV
# ══════════════════════════════════════════════════════════
def fetch_ohlcv(code):
    end   = datetime.date.today()
    start = end - datetime.timedelta(days=OHLCV_PERIOD)
    df = retry_call(fdr.DataReader, code, start, end)
    if df is None or df.empty: return None
    df = df.dropna(subset=["Close","Volume"])
    df = df[df["Volume"] > 0].copy()
    if len(df) < MIN_DAYS: return None
    avg_vol = df["Volume"].tail(20).mean()
    if avg_vol < MIN_AVG_VOL: return None
    return {
        "closes":    [safe_int(x) for x in df["Close"].tolist()],
        "highs":     [safe_int(x) for x in df["High"].tolist()],
        "lows":      [safe_int(x) for x in df["Low"].tolist()],
        "volumes":   [safe_int(x) for x in df["Volume"].tolist()],
        "avgVolume": safe_int(avg_vol),
    }

# ══════════════════════════════════════════════════════════
# 3. 네이버금융 수급 크롤링
# ══════════════════════════════════════════════════════════
def fetch_naver_supply(code):
    url = f"https://finance.naver.com/item/frgn.naver?code={code}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        res.encoding = "euc-kr"
        soup = BeautifulSoup(res.text, "lxml")
        table = soup.select_one("table.type2")
        if not table: return _def_supply()
        rows = table.select("tr")
        f_streak = i_streak = f_net = i_net = 0
        count = 0
        for row in rows:
            tds = row.select("td")
            if len(tds) < 5: continue
            try:
                fn   = safe_int(tds[3].get_text(strip=True).replace(",","").replace("+",""))
                inst = safe_int(tds[4].get_text(strip=True).replace(",","").replace("+",""))
                f_net += fn; i_net += inst
                if count == 0:
                    f_streak = 1 if fn > 0 else 0
                    i_streak = 1 if inst > 0 else 0
                else:
                    f_streak = f_streak+1 if fn>0 else 0
                    i_streak = i_streak+1 if inst>0 else 0
                count += 1
                if count >= 10: break
            except: continue
        return {"foreignBuyDays":f_streak,"institutionBuyDays":i_streak,
                "foreignNetBuy":f_net,"institutionNetBuy":i_net}
    except: return _def_supply()

def _def_supply():
    return {"foreignBuyDays":0,"institutionBuyDays":0,
            "foreignNetBuy":0,"institutionNetBuy":0}

# ══════════════════════════════════════════════════════════
# 4. 뉴스 감성
# ══════════════════════════════════════════════════════════
POS_KW = ["수주","계약","호실적","상향","매수","목표주가","신고가",
          "흑자","증가","성장","수익","돌파","강세","급등","어닝"]
NEG_KW = ["손실","적자","하락","하향","매도","리스크","위기","감소",
          "부진","우려","급락","충당금","소송","조사","제재"]

def fetch_news_sentiment(name):
    url = f"https://search.naver.com/search.naver?where=news&query={name}&sort=1&pd=4"
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "lxml")
        titles = [a.get_text(strip=True) for a in soup.select("a.news_tit")][:15]
        if not titles: return 50.0, []
        pos = [t for t in titles if any(k in t for k in POS_KW)]
        neg = [t for t in titles if any(k in t for k in NEG_KW)]
        sc = ((len(pos)-len(neg))/len(titles))*50+50
        reasons = [f"긍정 뉴스: {t[:18]}" for t in pos[:2]]
        return max(0.0,min(100.0,sc)), reasons
    except: return 50.0, []

# ══════════════════════════════════════════════════════════
# 5. DART 공시
# ══════════════════════════════════════════════════════════
DART_POS = ["자기주식취득","수주","공급계약","배당","영업이익"]
DART_NEG = ["유상증자","전환사채","대규모손실","불성실공시"]

def fetch_dart(code):
    if not DART_API_KEY: return 50.0, []
    try:
        today = datetime.date.today()
        bgn = (today-datetime.timedelta(days=7)).strftime("%Y%m%d")
        res = requests.get("https://opendart.fss.or.kr/api/list.json", timeout=8,
            params={"crtfc_key":DART_API_KEY,"corp_code":code,
                    "bgn_de":bgn,"end_de":today.strftime("%Y%m%d")})
        data = res.json()
        if data.get("status")!="000": return 50.0,[]
        sc=50.0; reasons=[]
        for item in data.get("list",[]):
            t=item.get("report_nm","")
            if any(k in t for k in DART_POS): sc+=15; reasons.append(f"공시: {t[:20]}")
            if any(k in t for k in DART_NEG): sc-=20
        return max(0.0,min(100.0,sc)), reasons
    except: return 50.0,[]

# ══════════════════════════════════════════════════════════
# 6. 섹터 모멘텀
# ══════════════════════════════════════════════════════════
def build_sector_returns(universe_df, ohlcv_cache):
    sr = {}
    for _, row in universe_df.iterrows():
        code=str(row["code"]); sec=str(row.get("sector","기타")) or "기타"
        if code not in ohlcv_cache: continue
        c=ohlcv_cache[code]["closes"]
        if len(c)<6: continue
        sr.setdefault(sec,[]).append((c[-1]-c[-6])/c[-6]*100)
    return {k:_avg(v) for k,v in sr.items() if v}

def calc_sector_score(sr, sector, kospi_ret):
    diff = sr.get(sector, kospi_ret) - kospi_ret
    if diff>=1.5: return 100.0
    if diff>=1.0: return 80.0
    if diff>=0.5: return 60.0
    if diff>=0.0: return 30.0
    return 0.0

# ══════════════════════════════════════════════════════════
# 7. 스코어링 엔진 (8팩터)
# ══════════════════════════════════════════════════════════
def _rsi(c,p=14):
    if len(c)<p+1: return 50.0
    g=l=0.0
    for i in range(len(c)-p,len(c)):
        d=c[i]-c[i-1]
        if d>0: g+=d
        else: l+=abs(d)
    ag,al=g/p,l/p
    return 100.0 if al==0 else 100-100/(1+ag/al)

def _ema(c,p):
    k=2/(p+1); e=float(c[0])
    for x in c[1:]: e=x*k+e*(1-k)
    return e

def _bb_pct(c,p=20):
    if len(c)<p: return 50.0
    sl=c[-p:]; m=_avg(sl); sd=_std(sl)
    if sd==0: return 50.0
    return ((c[-1]-(m-2*sd))/(4*sd))*100

def _atr_r(h,l,c,p=14):
    if len(c)<p+1: return 3.0
    trs=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(len(c)-p,len(c))]
    return (_avg(trs)/c[-1])*100 if c[-1]>0 else 3.0

def _ma_align(c):
    if len(c)<60: return 0
    l=c[-1]; m5=_avg(c[-5:]); m20=_avg(c[-20:]); m60=_avg(c[-60:])
    if l>m5>m20>m60: return 100
    if l>m20>m60: return 60
    if l>m60: return 30
    return 0

# ── 팩터1: 수급 25% ───────────────────────────────────────
def f1_supply(s):
    fd=s.get("foreignBuyDays",0); id_=s.get("institutionBuyDays",0)
    fn=s.get("foreignNetBuy",0); inst=s.get("institutionNetBuy",0)
    sc=0.0; r=[]
    if fd>=5: sc+=40; r.append(f"외국인 {fd}일 연속 순매수")
    elif fd>=3: sc+=30; r.append(f"외국인 {fd}일 연속 순매수")
    elif fd>=2: sc+=20; r.append(f"외국인 {fd}일 순매수")
    elif fd>=1: sc+=10; r.append("외국인 순매수")
    if id_>=4: sc+=35; r.append(f"기관 {id_}일 연속 순매수")
    elif id_>=3: sc+=25; r.append(f"기관 {id_}일 연속 순매수")
    elif id_>=2: sc+=15; r.append(f"기관 {id_}일 순매수")
    elif id_>=1: sc+=8; r.append("기관 순매수")
    if fn>0 and inst>0: sc+=25; r.append("외인·기관 동반 순매수")
    return min(100.0,sc), r

# ── 팩터2: 모멘텀 18% ─────────────────────────────────────
def f2_momentum(s):
    c=s.get("closes",[])
    if len(c)<20: return 50.0,[]
    sc=0.0; r=[]
    al=_ma_align(c); sc+=al*0.4
    if al==100: r.append("이동평균 완전 정배열 (5/20/60일)")
    elif al==60: r.append("이동평균 부분 정배열")
    rsi=_rsi(c)
    if 50<=rsi<=65: sc+=30; r.append(f"RSI {rsi:.0f} (상승 초입)")
    elif 65<rsi<=75: sc+=15; r.append(f"RSI {rsi:.0f} (상승 중)")
    elif 40<=rsi<50: sc+=15
    if len(c)>=26:
        e12=_ema(c,12); e26=_ema(c,26)
        pe12=_ema(c[:-1],12); pe26=_ema(c[:-1],26)
        if e12-e26>0 and pe12-pe26<=0: sc+=30; r.append("MACD 골든크로스 발생")
        elif e12>e26: sc+=15; r.append("MACD 양수 유지")
    return min(100.0,sc), r

# ── 팩터3: 거래량 15% ─────────────────────────────────────
def f3_volume(s):
    c=s.get("closes",[]); v=s.get("volumes",[])
    if len(v)<20: return 50.0,[]
    sc=0.0; r=[]
    avg20=_avg(v[-20:])
    if avg20==0: return 20.0,[]
    ratio=v[-1]/avg20
    is_up=len(c)>=2 and c[-1]>c[-2]
    if ratio>=3 and is_up: sc+=50; r.append(f"거래량 {ratio:.1f}배 급증 + 양봉")
    elif ratio>=2 and is_up: sc+=35; r.append(f"거래량 {ratio:.1f}배 증가 + 양봉")
    elif ratio>=1.5 and is_up: sc+=20; r.append(f"거래량 {ratio:.1f}배 증가")
    elif ratio>=1 and is_up: sc+=10
    if len(v)>=10:
        r5=_avg(v[-5:])/_avg(v[-10:-5]) if _avg(v[-10:-5])>0 else 1
        if r5>=1.5: sc+=30; r.append("5일 거래량 증가 추세")
        elif r5>=1.2: sc+=15
    if len(v)>=13:
        rb=_avg(v[-13:-3]); rb3=_avg(v[-3:])
        if rb>0 and rb3/rb>=2: sc+=20; r.append("저거래량 다지기 후 폭발 패턴")
    return min(100.0,sc), r

# ── 팩터4: 재무 13% ───────────────────────────────────────
def f4_fundamental(s):
    per=safe_float(s.get("per",0)); pbr=safe_float(s.get("pbr",0)); roe=safe_float(s.get("roe",0))
    sc=0.0; r=[]
    if 0<per<10: sc+=35; r.append(f"PER {per:.1f}배 (극도 저평가)")
    elif per<15: sc+=28; r.append(f"PER {per:.1f}배 (저평가)")
    elif per<20: sc+=18
    elif per<30: sc+=8
    if 0<pbr<0.8: sc+=30; r.append(f"PBR {pbr:.2f}배 (순자산 이하)")
    elif pbr<1.0: sc+=22; r.append(f"PBR {pbr:.2f}배 (저평가)")
    elif pbr<1.5: sc+=14
    elif pbr<2.0: sc+=6
    if roe>25: sc+=35; r.append(f"ROE {roe:.1f}% (최우수)")
    elif roe>=20: sc+=28; r.append(f"ROE {roe:.1f}%")
    elif roe>=15: sc+=20
    elif roe>=10: sc+=10
    elif roe>=5: sc+=4
    return min(100.0,sc), r

# ── 팩터5: 변동성 10% ─────────────────────────────────────
def f5_volatility(s):
    c=s.get("closes",[]); h=s.get("highs",[]); l=s.get("lows",[])
    if len(c)<20: return 50.0,[]
    sc=50.0; r=[]
    bb=_bb_pct(c)
    if bb<15: sc+=45; r.append("볼린저밴드 하단 반등 신호")
    elif bb<25: sc+=35; r.append("볼린저밴드 하단 근접")
    elif bb<40: sc+=20
    elif bb>85: sc-=25; r.append("볼린저밴드 상단 과열")
    atr=_atr_r(h,l,c)
    if atr<1.5: sc+=10
    elif atr>5: sc-=20
    return min(100.0,max(0.0,sc)), r

# ── 팩터6: 뉴스/공시 10% ─────────────────────────────────
def f6_news(s):
    ns=safe_float(s.get("newsSentiment",50))
    ds=safe_float(s.get("dartScore",50))
    r=list(s.get("dartReasons",[]))+list(s.get("newsReasons",[]))
    if not DART_API_KEY: return ns, r
    return ns*0.5+ds*0.5, r

# ── 팩터7: 섹터 5% ───────────────────────────────────────
def f7_sector(s):
    sc=safe_float(s.get("sectorScore",30)); r=[]
    if sc>=80: r.append(f"{s.get('sector','해당 섹터')} 강세 순환매")
    return sc, r

# ── 팩터8: 단기 수익률 4% (신규) ─────────────────────────
def f8_short_return(s):
    c=s.get("closes",[])
    if len(c)<6: return 50.0,[]
    sc=0.0; r=[]
    ret3=(c[-1]-c[-4])/c[-4]*100 if len(c)>=4 else 0
    ret5=(c[-1]-c[-6])/c[-6]*100 if len(c)>=6 else 0
    if ret3>=3: sc+=50; r.append(f"최근 3일 +{ret3:.1f}% 상승 중")
    elif ret3>=1: sc+=30; r.append(f"최근 3일 +{ret3:.1f}%")
    elif ret3>=0: sc+=15
    elif ret3<-5: sc-=20
    if ret5>=5: sc+=40; r.append(f"최근 5일 +{ret5:.1f}% 강한 추세")
    elif ret5>=2: sc+=25
    elif ret5>=0: sc+=10
    elif ret5<-8: sc-=20
    return min(100.0,max(0.0,sc)), r

# ── 종합 스코어 + JSON 구조화 ─────────────────────────────
def calc_composite(s):
    sc1,r1=f1_supply(s)
    sc2,r2=f2_momentum(s)
    sc3,r3=f3_volume(s)
    sc4,r4=f4_fundamental(s)
    sc5,r5=f5_volatility(s)
    sc6,r6=f6_news(s)
    sc7,r7=f7_sector(s)
    sc8,r8=f8_short_return(s)

total=(sc1*.25+sc2*.18+sc3*.15+sc4*.13+
       sc5*.10+sc6*.10+sc7*.05+sc8*.04)

# 점수 높은 팩터 순으로 reason 최대 4개
pairs = sorted([(sc1, r1), (sc2, r2), (sc3, r3), (sc4, r4),
                (sc5, r5), (sc6, r6), (sc7, r7), (sc8, r8)], key=lambda x: -x[0])
reasons=[]
    for _,rs in pairs:
        for x in rs:
            if x not in reasons: reasons.append(x)
        if len(reasons)>=4: break

    risk=_auto_risk(s,sc1,sc2,sc5,sc8)

    return {
        "total": round(total,1),
        "breakdown": {
            "supply":      round(sc1,1),
            "momentum":    round(sc2,1),
            "volume":      round(sc3,1),
            "fundamental": round(sc4,1),
            "volatility":  round(sc5,1),
            "news":        round(sc6,1),
            "sector":      round(sc7,1),
            "shortReturn": round(sc8,1),
        },
        "reasons": reasons[:4],   # ← 구조화된 이유 배열
        "risk":    risk,           # ← 자동 생성 리스크
    }

def _auto_risk(s,sc1,sc2,sc5,sc8):
    c=s.get("closes",[])
    if sc8>=70 and sc2>=70: return "단기 과열 구간 — 분할 매수 권장"
    if sc5<=30: return "변동성 높음 — 손절 라인 설정 필수"
    if sc1<=20: return "수급 뒷받침 부족 — 추가 확인 필요"
    if len(c)>=2:
        chg=(c[-1]-c[-2])/c[-2]*100
        if chg>=5: return f"당일 급등 {chg:.1f}% — 추격 매수 주의"
    return "단기 시장 변동성에 따른 조정 가능성 유의"

# ── 리스크 필터 ───────────────────────────────────────────
def risk_check(s):
    c=s.get("closes",[])
    if len(c)<5: return False
    if len(c)>=2:
        chg=(c[-1]-c[-2])/c[-2]*100
        if chg>=28: return False
        if len(c)>=4:
            if all((c[i]-c[i-1])/c[i-1]*100>=5 for i in range(-3,0)): return False
    if len(c)>=60:
        if c[-1]==min(c[-60:]): return False
    return True

# ══════════════════════════════════════════════════════════
# 8. TOP 10 (섹터 분산)
# ══════════════════════════════════════════════════════════
def select_top10(stocks):
    ss=sorted(stocks,key=lambda x:x["score"]["total"],reverse=True)
    sc={}; result=[]
    for s in ss:
        sec=s.get("sector","기타") or "기타"
        if sc.get(sec,0)>=2: continue
        sc[sec]=sc.get(sec,0)+1
        result.append(s)
        if len(result)>=TOP_N: break
    if len(result)<TOP_N:
        have={s["code"] for s in result}
        for s in ss:
            if s["code"] not in have: result.append(s)
            if len(result)>=TOP_N: break
    return result[:TOP_N]

# ══════════════════════════════════════════════════════════
# 9. 성과 추적
# ══════════════════════════════════════════════════════════
def update_history_results():
    """전일 추천 종목 수익률 업데이트"""
    hp="data/history.json"
    if not os.path.exists(hp): return
    try:
        history=json.load(open(hp,encoding="utf-8"))
        today=datetime.date.today()
        updated=0
        for entry in history:
            if entry.get("result")!="pending": continue
            ed=datetime.date.fromisoformat(entry["date"])
            days=(today-ed).days
            if days<=0 or days>7: continue
            try:
                df=fdr.DataReader(entry["code"],today-datetime.timedelta(days=5),today)
                if df.empty: continue
                cp=safe_int(df["Close"].iloc[-1])
                ep=entry.get("entryPrice",cp)
                ret=round((cp-ep)/ep*100,2) if ep>0 else 0
                entry["currentPrice"]=cp
                entry["returnRate"]=ret
                entry["result"]="hit" if ret>=3.0 else ("miss" if days>=5 else "pending")
                updated+=1
            except: continue
        if updated>0:
            with open(hp,"w",encoding="utf-8") as f:
                json.dump(history,f,ensure_ascii=False,separators=(",",":"))
            print(f"  → {updated}건 성과 업데이트")
    except Exception as e:
        print(f"  ⚠️ 히스토리 업데이트 오류: {e}")

def save_today_picks(top10, date_str):
    hp="data/history.json"
    try: history=json.load(open(hp,encoding="utf-8")) if os.path.exists(hp) else []
    except: history=[]
    history=[h for h in history if h.get("date")!=date_str]
    for rank,s in enumerate(top10,1):
        history.append({
            "date":date_str,"rank":rank,
            "code":s["code"],"name":s["name"],
            "entryPrice":s.get("price",0),
            "currentPrice":s.get("price",0),
            "returnRate":0.0,
            "score":s["score"]["total"],
            "reasons":s["score"]["reasons"],
            "risk":s["score"]["risk"],
            "result":"pending",
        })
    cutoff=(datetime.date.today()-datetime.timedelta(days=90)).isoformat()
    history=[h for h in history if h.get("date","")>=cutoff]
    with open(hp,"w",encoding="utf-8") as f:
        json.dump(history,f,ensure_ascii=False,separators=(",",":"))
    print(f"  → history.json 저장 ({len(history)}건)")

def calc_hit_stats():
    hp="data/history.json"
    if not os.path.exists(hp):
        return {"hitRate":0,"totalPicks":0,"hits":0,"avgReturn":0}
    try:
        h=json.load(open(hp,encoding="utf-8"))
        done=[x for x in h if x.get("result") in ["hit","miss"]]
        hits=[x for x in done if x.get("result")=="hit"]
        rate=round(len(hits)/len(done)*100,1) if done else 0
        avg_ret=round(_avg([x.get("returnRate",0) for x in done]),2) if done else 0
        return {"hitRate":rate,"totalPicks":len(done),
                "hits":len(hits),"avgReturn":avg_ret}
    except: return {"hitRate":0,"totalPicks":0,"hits":0,"avgReturn":0}

# ══════════════════════════════════════════════════════════
# 10. 메인
# ══════════════════════════════════════════════════════════
def main():
    t0=time.time(); today=datetime.date.today()
    print(f"\n{'='*58}")
    print(f"  🚀 AI 주식 분석 엔진 v4.0 — {today}")
    print(f"{'='*58}\n")

    # 전일 성과 업데이트
    print("📊 전일 추천 성과 업데이트...")
    update_history_results()
    hit_stats=calc_hit_stats()
    print(f"  → 누적 적중률: {hit_stats['hitRate']}% "
          f"({hit_stats['hits']}/{hit_stats['totalPicks']}건) "
          f"평균수익률: {hit_stats['avgReturn']}%\n")

    # 종목 로딩
    universe_df=load_universe(); total=len(universe_df)

    # OHLCV
    print(f"📈 OHLCV 수집 ({total:,}개)...")
    ohlcv_cache={}; raw=[]; failed=0
    for idx,row in universe_df.iterrows():
        code=str(row["code"]).zfill(6)
        if idx%100==0 and idx>0:
            print(f"  [{idx:4d}/{total}] {idx/total*100:.1f}% | {time.time()-t0:.0f}초 | {len(raw)}개")
        ohlcv=fetch_ohlcv(code)
        if not ohlcv: failed+=1; continue
        ohlcv_cache[code]=ohlcv
        raw.append({
            "code":code,"name":str(row["name"]),
            "market":str(row["market"]),"sector":str(row.get("sector","")) or "기타",
            **ohlcv,
            "per":safe_float(row.get("per",0),15.0),
            "pbr":safe_float(row.get("pbr",0),1.0),
            "roe":safe_float(row.get("roe",0),8.0),
            "marcap":safe_int(row.get("marcap",0)),
        })
    print(f"\n  → 완료: {len(raw)}개 성공 / {failed}개 실패")

    # 섹터 모멘텀
    print("\n📊 섹터 모멘텀...")
    sr=build_sector_returns(universe_df,ohlcv_cache)
    kospi_ret=0.0
    kdf=retry_call(fdr.DataReader,"KS11",today-datetime.timedelta(days=14),today)
    if kdf is not None and len(kdf)>=6:
        ck=kdf["Close"].tolist()
        kospi_ret=(ck[-1]-ck[-6])/ck[-6]*100
    print(f"  → KOSPI 5일: {kospi_ret:.2f}%")

    # 수급/뉴스 (시총 상위 300개)
    print("\n💹 수급/뉴스 수집...")
    top300={s["code"] for s in sorted(raw,key=lambda x:x.get("marcap",0),reverse=True)[:300]}
    for i,s in enumerate(raw):
        code=s["code"]; sec=s.get("sector","기타") or "기타"
        s["sectorScore"]=calc_sector_score(sr,sec,kospi_ret)
        if code in top300:
            if i%60==0: print(f"  {i}/{len(raw)} 수급수집...")
            s.update(fetch_naver_supply(code))
            sent,nr=fetch_news_sentiment(s["name"])
            s["newsSentiment"]=sent; s["newsReasons"]=nr
            ds,dr=fetch_dart(code)
            s["dartScore"]=ds; s["dartReasons"]=dr
            time.sleep(0.25)
        else:
            s.update(_def_supply())
            s["newsSentiment"]=50.0; s["newsReasons"]=[]
            s["dartScore"]=50.0; s["dartReasons"]=[]

    # 스코어링
    print("\n🧠 8팩터 스코어링...")
    scored=[{**s,"score":calc_composite(s)} for s in raw if risk_check(s)]
    print(f"  → {len(scored)}개")

    # TOP 10
    top10=select_top10(scored)
    for i,s in enumerate(top10,1): s["rank"]=i

    # 출력
    print(f"\n{'='*58}")
    for s in top10:
        print(f"  {s['rank']:2d}. {s['name']:12s} [{s['code']}] 점수:{s['score']['total']:5.1f}")
        print(f"      ✅ {' / '.join(s['score']['reasons'][:2])}")
        print(f"      ⚠️  {s['score']['risk']}")

    # 저장
    print("\n💾 저장 중...")
    os.makedirs("data",exist_ok=True)
    save_today_picks(top10,str(today))

    save=[]
    for s in top10:
        d={k:v for k,v in s.items() if k not in ["closes","highs","lows","volumes"]}
        d["closes"]=s["closes"][-60:]
        d["volumes"]=s["volumes"][-60:]
        save.append(d)

    out={
        "date":str(today),
        "generatedAt":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totalAnalyzed":len(scored),
        "dartEnabled":bool(DART_API_KEY),
        "hitStats":hit_stats,
        "stocks":save,
    }
    with open("data/daily_stocks.json","w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,separators=(",",":"))

    elapsed=time.time()-t0
    print(f"\n✅ 완료! {elapsed/60:.1f}분 소요")
    print(f"   적중률: {hit_stats['hitRate']}% | 평균수익률: {hit_stats['avgReturn']}%\n")

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(f"\n❌ {e}"); traceback.print_exc(); sys.exit(1)
      
