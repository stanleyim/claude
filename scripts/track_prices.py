# -*- coding: utf-8 -*-
"""
성과 추적 엔진
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
매일 실행 → 과거 추천 종목 현재가 업데이트
D+1 / D+3 / D+5 / D+10 / D+20 수익률 자동 계산
→ data/tracking.json 저장
"""

import json, os, time, datetime, traceback
import FinanceDataReader as fdr

TRACK_DAYS = [1, 3, 5, 10, 20]
HIT_THRESHOLD = 3.0  # +3% 이상 = 적중

def safe_pct(a, b):
    try:
        if not b: return 0
        return round((a-b)/b*100, 2)
    except: return 0

def load_tracking():
    path = "data/tracking.json"
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return []

def save_tracking(data):
    os.makedirs("data", exist_ok=True)
    with open("data/tracking.json","w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))

def get_current_price(code):
    try:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=10)
        df = fdr.DataReader(code, start, today)
        if df is None or df.empty: return None
        return int(df["Close"].iloc[-1])
    except: return None

def main():
    today = datetime.date.today()
    print(f"\n{'='*52}")
    print(f"  📊 성과 추적 업데이트 — {today}")
    print(f"{'='*52}\n")

    # 오늘 추천 종목 로드 → tracking에 추가
    daily_path = "data/daily_stocks.json"
    tracking   = load_tracking()

    if os.path.exists(daily_path):
        try:
            with open(daily_path, encoding="utf-8") as f:
                daily = json.load(f)
            date_str = daily.get("date", str(today))

            # 오늘 날짜 중복 체크
            existing_dates = {t["entryDate"] for t in tracking}
            if date_str not in existing_dates:
                for s in daily.get("stocks", []):
                    tracking.append({
                        "entryDate":   date_str,
                        "rank":        s.get("rank", 0),
                        "code":        s["code"],
                        "name":        s["name"],
                        "entryPrice":  s.get("price", 0),
                        "score":       s.get("score",{}).get("total", 0),
                        "reasons":     s.get("score",{}).get("reasons", []),
                        "risk":        s.get("score",{}).get("risk", ""),
                        "tracking":    {},
                        "result":      "pending",
                        "finalReturn": 0,
                    })
                print(f"  → 오늘 추천 {len(daily.get('stocks',[]))}개 추가")
        except Exception as e:
            print(f"  ⚠️ daily_stocks 로드 오류: {e}")

    # 과거 추천 종목 가격 업데이트
    updated = 0
    for entry in tracking:
        entry_date  = datetime.date.fromisoformat(entry["entryDate"])
        days_elapsed = (today - entry_date).days
        entry_price  = entry.get("entryPrice", 0)

        if days_elapsed <= 0: continue
        if days_elapsed > 25: continue  # 25일 지난 건 스킵

        code = entry["code"]
        current_price = get_current_price(code)
        if not current_price: continue

        # D+N 수익률 계산
        for d in TRACK_DAYS:
            key = f"D{d}"
            if key in entry["tracking"]: continue  # 이미 기록됨

            # 거래일 기준으로 대략 날짜 계산
            target_date = entry_date + datetime.timedelta(days=d+3)
            if today >= target_date:
                ret = safe_pct(current_price, entry_price)
                entry["tracking"][key] = {
                    "price": current_price,
                    "ret":   ret,
                }

        # 최종 결과 판정 (D+5 기준)
        if "D5" in entry["tracking"]:
            ret5 = entry["tracking"]["D5"]["ret"]
            entry["finalReturn"] = ret5
            entry["result"] = "hit" if ret5 >= HIT_THRESHOLD else "miss"
        elif days_elapsed >= 8 and entry["tracking"]:
            last_ret = list(entry["tracking"].values())[-1]["ret"]
            entry["finalReturn"] = last_ret
            entry["result"] = "hit" if last_ret >= HIT_THRESHOLD else "miss"

        updated += 1
        time.sleep(0.1)

    print(f"  → {updated}건 가격 업데이트")

    # 90일 이전 데이터 정리
    cutoff = (today - datetime.timedelta(days=90)).isoformat()
    tracking = [t for t in tracking if t["entryDate"] >= cutoff]

    save_tracking(tracking)
    print(f"  → tracking.json 저장 ({len(tracking)}건)\n")
    print("✅ 성과 추적 완료!\n")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        traceback.print_exc()
      
