# -*- coding: utf-8 -*-

import FinanceDataReader as fdr
import datetime, json, os

START_DATE = "2025-01-01"
END_DATE   = "2025-04-01"
TOP_N = 5

# ================= 유틸 =================

def pct(a,b):
    return (a-b)/b*100 if b != 0 else 0

def avg(arr):
    return sum(arr)/len(arr) if arr else 0

# ================= 데이터 =================

def get_price(code, start, end):
    try:
        df = fdr.DataReader(code, start, end)
        if df is None or len(df) < 30:
            return None
        return df
    except:
        return None

# ================= 팩터 =================

def momentum(df):
    closes = df["Close"].tolist()
    if len(closes) < 20:
        return 0

    ma5 = avg(closes[-5:])
    ma20 = avg(closes[-20:])

    if closes[-1] > ma5 > ma20:
        return 100
    elif closes[-1] > ma20:
        return 70
    return 40

def volume(df):
    v = df["Volume"].tolist()
    if len(v) < 20:
        return 0

    ratio = v[-1] / avg(v[-20:])
    if ratio > 2:
        return 100
    elif ratio > 1.5:
        return 70
    return 40

# ================= 전략 =================

def score(df):
    return momentum(df)*0.6 + volume(df)*0.4

# ================= 백테스트 =================

def backtest():

    codes = fdr.StockListing("KOSPI").head(100)["Code"].tolist()

    date_range = fdr.DataReader("KS11", START_DATE, END_DATE).index

    results = []

    for i in range(30, len(date_range)-1):

        today = date_range[i]
        next_day = date_range[i+1]

        picks = []

        for code in codes:

            df = get_price(code, date_range[0], today)
            if df is None or len(df) < 30:
                continue

            df_slice = df.loc[:today]

            sc = score(df_slice)

            if sc < 70:
                continue

            price_today = df_slice["Close"].iloc[-1]

            try:
                df_next = fdr.DataReader(code, today, next_day)
                price_next = df_next["Close"].iloc[-1]
            except:
                continue

            ret = pct(price_next, price_today)

            picks.append(ret)

        if picks:
            picks = sorted(picks, reverse=True)[:TOP_N]
            results.append(avg(picks))

    # ================= 결과 =================

    win = len([x for x in results if x > 0])
    total = len(results)

    hit_rate = (win / total * 100) if total else 0
    avg_return = avg(results)

    print("===== BACKTEST RESULT =====")
    print("총 거래일:", total)
    print("승률:", round(hit_rate,1), "%")
    print("평균 수익:", round(avg_return,2), "%")

    os.makedirs("data", exist_ok=True)

    with open("data/backtest.json","w") as f:
        json.dump({
            "hit_rate": hit_rate,
            "avg_return": avg_return,
            "days": total
        }, f)

# ================= 실행 =================

if __name__ == "__main__":
    backtest()
