# -*- coding: utf-8 -*-

import json, os, sys, time, math, datetime, traceback
import requests
import FinanceDataReader as fdr
from bs4 import BeautifulSoup

TOP_N = 10
MIN_DAYS = 60
MIN_AVG_VOL = 30000

# ================= 유틸 =================

def safe_pct(a, b):
    try:
        if b in [0, None]:
            return 0
        return (a - b) / b * 100
    except:
        return 0

def avg(arr):
    return sum(arr)/len(arr) if arr else 0

# ================= 데이터 =================

def fetch_ohlcv(code):
    try:
        df = fdr.DataReader(code)
        if df is None or len(df) < MIN_DAYS:
            return None

        df = df.dropna(subset=["Close","Volume"])
        if len(df) < MIN_DAYS:
            return None

        if df["Volume"].tail(20).mean() < MIN_AVG_VOL:
            return None

        return {
            "closes": df["Close"].tolist(),
            "volumes": df["Volume"].tolist()
        }
    except:
        return None

# ================= 수급 =================

def fetch_supply(code):
    try:
        url = f"https://finance.naver.com/item/frgn.naver?code={code}"
        res = requests.get(url, timeout=5)
        res.encoding = "euc-kr"

        soup = BeautifulSoup(res.text, "lxml")
        rows = soup.select("table.type2 tr")

        f_days = i_days = 0

        for r in rows[:10]:
            t = r.select("td")
            if len(t) < 5:
                continue

            f = int(t[3].text.replace(",", "") or 0)
            i = int(t[4].text.replace(",", "") or 0)

            if f > 0:
                f_days += 1
            if i > 0:
                i_days += 1

        score = 0
        if f_days >= 3:
            score += 50
        if i_days >= 3:
            score += 50

        return score

    except:
        return 50

# ================= 팩터 =================

def f_momentum(c):
    if len(c) < 60:
        return 50

    ma5 = avg(c[-5:])
    ma20 = avg(c[-20:])
    ma60 = avg(c[-60:])

    if c[-1] > ma5 > ma20 > ma60:
        return 90
    elif c[-1] > ma20:
        return 70

    return 40

def f_volume(v):
    if len(v) < 20:
        return 50

    ratio = v[-1] / avg(v[-20:])

    if ratio > 2:
        return 80
    elif ratio > 1.5:
        return 60

    return 40

def f_short(c):
    chg = safe_pct(c[-1], c[-2])
    if chg > 3:
        return 80
    elif chg < -3:
        return 20
    return 50

# ================= 필터 =================

def elite_filter(s):
    c = s["closes"]
    v = s["volumes"]
    score = s["score"]["total"]

    if score < 65:
        return False

    if safe_pct(c[-1], c[-2]) > 8:
        return False

    if len(c) >= 4:
        if all(safe_pct(c[i], c[i-1]) > 5 for i in range(-3,0)):
            return False

    if c[-1] < avg(c[-20:]):
        return False

    if avg(v[-5:]) < avg(v[-20:]) * 0.8:
        return False

    return True


def super_filter(c):
    if len(c) < 60:
        return False

    ma20 = avg(c[-20:])
    ma60 = avg(c[-60:])

    if not (c[-1] > ma20 > ma60):
        return False

    recent_low = min(c[-5:])
    if recent_low < ma20 * 0.97:
        return True

    return False

# ================= 스코어 =================

def calc_score(s):
    c = s["closes"]
    v = s["volumes"]

    sc1 = fetch_supply(s["code"])
    sc2 = f_momentum(c)
    sc3 = f_volume(v)
    sc4 = f_short(c)

    total = sc1*0.3 + sc2*0.3 + sc3*0.2 + sc4*0.2

    return {"total": round(total,1)}

# ================= 리포트 =================

def generate_report(stocks):
    report = []
    for s in stocks:
        line = {
            "code": s["code"],
            "name": s["name"],
            "score": s["score"]["total"],
            "comment": "상승 가능성 높음 (AI 분석)"
        }
        report.append(line)

    with open("data/report.json","w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False)

# ================= 실행 =================

def main():
    print("START")

    df = fdr.StockListing("KOSPI").head(200)

    results = []

    for _, row in df.iterrows():
        code = str(row["Code"]).zfill(6)
        name = row["Name"]

        data = fetch_ohlcv(code)
        if not data:
            continue

        s = {"code":code, "name":name, **data}

        s["score"] = calc_score(s)

        if elite_filter(s) and super_filter(s["closes"]):
            results.append(s)

    results = sorted(results, key=lambda x: x["score"]["total"], reverse=True)[:TOP_N]

    for i, s in enumerate(results,1):
        print(i, s["name"], s["score"])

    os.makedirs("data", exist_ok=True)

    with open("data/daily_stocks.json","w",encoding="utf-8") as f:
        json.dump(results,f,ensure_ascii=False)

    generate_report(results)

    print("DONE")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        sys.exit(1)
