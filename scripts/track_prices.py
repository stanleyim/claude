# -*- coding: utf-8 -*-
"""
성과 추적 엔진 (FIXED VERSION)
"""

import json, os, time, datetime, traceback
import FinanceDataReader as fdr

TRACK_DAYS = [1, 3, 5, 10, 20]
HIT_THRESHOLD = 3.0


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
    except:
        pass
    return []


def save_tracking(data):
    os.makedirs("data", exist_ok=True)
    with open("data/tracking.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def get_current_price(code):
    try:
        today = datetime.date.today()
        start = today - datetime.timedelta(days=10)
        df = fdr.DataReader(code, start, today)
        if df is None or df.empty:
            return None
        return float(df["Close"].iloc[-1])
    except:
        return None


def main():
    today = datetime.date.today()
    print("\n" + "=" * 52)
    print(f"  📊 성과 추적 업데이트 — {today}")
    print("=" * 52 + "\n")

    daily_path = "data/daily_stocks.json"
    tracking = load_tracking()

    # ─────────────────────────────
    # 1. 오늘 데이터 추가
    # ─────────────────────────────
    if os.path.exists(daily_path):
        with open(daily_path, encoding="utf-8") as f:
            daily = json.load(f)

        date_str = daily.get("date", str(today))
        existing_dates = {t["entryDate"] for t in tracking}

        if date_str not in existing_dates:
            for s in daily.get("stocks", []):
                tracking.append({
                    "entryDate": date_str,
                    "rank": s.get("rank", 0),
                    "code": s["code"],
                    "name": s["name"],
                    "entryPrice": float(s.get("price", 0)),
                    "score": s.get("score", {}).get("total", 0),
                    "tracking": {},
                    "result": "pending",
                    "finalReturn": 0.0,
                })
            print(f"  → 오늘 추천 {len(daily.get('stocks', []))}개 추가")

    # ─────────────────────────────
    # 2. 가격 업데이트 + 수익 계산
    # ─────────────────────────────
    updated = 0

    for entry in tracking:
        try:
            entry_date = datetime.date.fromisoformat(entry["entryDate"])
        except:
            continue

        if (today - entry_date).days <= 0:
            continue

        code = entry["code"]
        entry_price = entry.get("entryPrice", 0)
        if entry_price <= 0:
            continue

        current_price = get_current_price(code)
        if not current_price:
            continue

        # ─ D수익률 업데이트
        returns = []

        for d in TRACK_DAYS:
            key = f"D{d}"
            if key in entry["tracking"]:
                returns.append(entry["tracking"][key]["ret"])
                continue

            ret = safe_pct(current_price, entry_price)
            entry["tracking"][key] = {
                "price": current_price,
                "ret": ret
            }
            returns.append(ret)

        # ─ 핵심 FIX: 최고 수익률 기준 finalReturn
        if returns:
            best_ret = max(returns)
            entry["finalReturn"] = best_ret
            entry["result"] = "hit" if best_ret >= HIT_THRESHOLD else "miss"

        updated += 1
        time.sleep(0.1)

    print(f"  → {updated}건 업데이트")

    # ─────────────────────────────
    # 3. 오래된 데이터 제거
    # ─────────────────────────────
    cutoff = (today - datetime.timedelta(days=90)).isoformat()
    tracking = [t for t in tracking if t["entryDate"] >= cutoff]

    save_tracking(tracking)

    print(f"  → tracking.json 저장 ({len(tracking)}건)")
    print("\n✅ 성과 추적 완료!\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 오류:", e)
        traceback.print_exc()
