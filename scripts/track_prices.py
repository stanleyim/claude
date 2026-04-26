# -*- coding: utf-8 -*-
"""
성과 추적 엔진 (FINAL FIXED VERSION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 실제 가격 기반 수익률 계산
- price 누락 fallback 처리
- finalReturn 항상 생성
- stats 정상화
"""

import json, os, time, datetime, traceback
import FinanceDataReader as fdr

TRACK_DAYS = [1, 3, 5, 10, 20]
HIT_THRESHOLD = 3.0


def safe_pct(a, b):
    try:
        if not b:
            return 0.0
        return round((a - b) / b * 100, 2)
    except:
        return 0.0


def load_tracking():
    path = "data/tracking.json"
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []


def save_tracking(data):
    os.makedirs("data", exist_ok=True)
    with open("data/tracking.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def get_price(code, entry_price):
    """
    안정형 가격 함수
    - 실패 시 entry_price fallback
    """
    try:
        df = fdr.DataReader(code)
        if df is None or df.empty:
            return entry_price
        price = df["Close"].iloc[-1]
        return float(price) if price else entry_price
    except:
        return entry_price


def main():
    today = datetime.date.today()
    print("\n" + "=" * 52)
    print(f"  📊 성과 추적 업데이트 — {today}")
    print("=" * 52 + "\n")

    tracking = load_tracking()

    # ─────────────────────────────
    # 1. daily_stocks 반영
    # ─────────────────────────────
    daily_path = "data/daily_stocks.json"

    if os.path.exists(daily_path):
        try:
            with open(daily_path, encoding="utf-8") as f:
                daily = json.load(f)

            date_str = daily.get("date", str(today))
            existing = {t["entryDate"] for t in tracking}

            if date_str not in existing:
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
                print(f"  → 오늘 종목 {len(daily.get('stocks', []))}개 추가")

        except Exception as e:
            print("daily error:", e)

    # ─────────────────────────────
    # 2. 수익률 계산
    # ─────────────────────────────
    updated = 0

    for entry in tracking:
        try:
            entry_date = datetime.date.fromisoformat(entry["entryDate"])
        except:
            continue

        if (today - entry_date).days <= 0:
            continue

        entry_price = float(entry.get("entryPrice", 0))
        if entry_price <= 0:
            continue

        code = entry["code"]

        # ✔ 핵심: 무조건 가격 확보 (fallback 포함)
        current_price = get_price(code, entry_price)

        returns = []

        # ─ D수익률 계산
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

        # ─ finalReturn = 최고 수익률
        if returns:
            best = max(returns)
            entry["finalReturn"] = best
            entry["result"] = "hit" if best >= HIT_THRESHOLD else "miss"

        updated += 1
        time.sleep(0.05)

    print(f"  → {updated}건 업데이트 완료")

    # ─────────────────────────────
    # 3. 오래된 데이터 정리
    # ─────────────────────────────
    cutoff = (today - datetime.timedelta(days=90)).isoformat()
    tracking = [t for t in tracking if t["entryDate"] >= cutoff]

    save_tracking(tracking)

    print(f"  → tracking.json 저장 완료 ({len(tracking)}건)")
    print("\n✅ 성과 추적 완료!\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 오류:", e)
        traceback.print_exc()
