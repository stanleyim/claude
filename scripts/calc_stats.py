# -*- coding: utf-8 -*-
"""
통계 자동 계산 엔진
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tracking.json 읽어서 다각도 통계 자동 산출
→ data/stats.json 저장
→ 대시보드에서 실시간 표시
"""

import json, os, datetime, traceback
from collections import defaultdict

def load_tracking():
    try:
        with open("data/tracking.json", encoding="utf-8") as f:
            return json.load(f)
    except: return []

def avg(arr):
    return round(sum(arr)/len(arr), 2) if arr else 0

def hit_rate(arr):
    if not arr: return 0
    return round(len([x for x in arr if x >= 3.0]) / len(arr) * 100, 1)

def main():
    today = datetime.date.today()
    print(f"\n{'='*52}")
    print(f"  📈 통계 계산 — {today}")
    print(f"{'='*52}\n")

    tracking = load_tracking()
    done = [t for t in tracking if t["result"] in ["hit","miss"]]

    if not done:
        print("  ⚠️ 완료된 데이터 없음 — 아직 통계 없음")
        output = {
            "updatedAt":  str(today),
            "hasData":    False,
            "message":    "데이터 축적 중입니다. 5거래일 후부터 통계가 표시됩니다.",
        }
        os.makedirs("data", exist_ok=True)
        with open("data/stats.json","w",encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        return

    returns = [t["finalReturn"] for t in done]

    # ── 1. 전체 통계 ──────────────────────────
    overall = {
        "totalPicks":  len(done),
        "hits":        len([t for t in done if t["result"]=="hit"]),
        "hitRate":     hit_rate(returns),
        "avgReturn":   avg(returns),
        "bestReturn":  round(max(returns), 2),
        "worstReturn": round(min(returns), 2),
    }
    print(f"  전체 적중률: {overall['hitRate']}% ({overall['hits']}/{overall['totalPicks']})")
    print(f"  평균 수익률: {overall['avgReturn']}%")

    # ── 2. 순위별 적중률 ──────────────────────
    by_rank = defaultdict(list)
    for t in done:
        by_rank[t.get("rank", 0)].append(t["finalReturn"])
    rank_stats = {
        f"{r}위": {
            "hitRate":   hit_rate(rets),
            "avgReturn": avg(rets),
            "count":     len(rets),
        }
        for r, rets in sorted(by_rank.items())
    }

    # ── 3. 요일별 적중률 ──────────────────────
    DAY_KR = ["월","화","수","목","금","토","일"]
    by_day = defaultdict(list)
    for t in done:
        try:
            d = datetime.date.fromisoformat(t["entryDate"]).weekday()
            by_day[DAY_KR[d]].append(t["finalReturn"])
        except: continue
    day_stats = {
        day: {
            "hitRate":   hit_rate(rets),
            "avgReturn": avg(rets),
            "count":     len(rets),
        }
        for day, rets in by_day.items()
    }

    # ── 4. 점수대별 적중률 ────────────────────
    score_buckets = defaultdict(list)
    for t in done:
        sc = t.get("score", 0)
        if sc >= 85:   bucket = "85점 이상"
        elif sc >= 80: bucket = "80~84점"
        elif sc >= 75: bucket = "75~79점"
        elif sc >= 70: bucket = "70~74점"
        else:          bucket = "70점 미만"
        score_buckets[bucket].append(t["finalReturn"])
    score_stats = {
        b: {
            "hitRate":   hit_rate(rets),
            "avgReturn": avg(rets),
            "count":     len(rets),
        }
        for b, rets in score_buckets.items()
    }

    # ── 5. 월별 적중률 ────────────────────────
    by_month = defaultdict(list)
    for t in done:
        try:
            m = t["entryDate"][:7]  # YYYY-MM
            by_month[m].append(t["finalReturn"])
        except: continue
    month_stats = {
        m: {
            "hitRate":   hit_rate(rets),
            "avgReturn": avg(rets),
            "count":     len(rets),
        }
        for m, rets in sorted(by_month.items())
    }

    # ── 6. 최근 30일 추천 히스토리 ───────────
    recent = sorted(done, key=lambda x: x["entryDate"], reverse=True)[:30]
    recent_list = [{
        "date":        t["entryDate"],
        "rank":        t.get("rank", 0),
        "name":        t["name"],
        "code":        t["code"],
        "entryPrice":  t["entryPrice"],
        "finalReturn": t["finalReturn"],
        "result":      t["result"],
        "reasons":     t.get("reasons", []),
    } for t in recent]

    # ── 7. 베스트 / 워스트 종목 ───────────────
    best5  = sorted(done, key=lambda x: x["finalReturn"], reverse=True)[:5]
    worst5 = sorted(done, key=lambda x: x["finalReturn"])[:5]

    def fmt(t):
        return {
            "date":   t["entryDate"],
            "name":   t["name"],
            "ret":    t["finalReturn"],
            "result": t["result"],
        }

    # ── 저장 ──────────────────────────────────
    output = {
        "updatedAt": str(today),
        "hasData":   True,
        "overall":   overall,
        "byRank":    rank_stats,
        "byDay":     day_stats,
        "byScore":   score_stats,
        "byMonth":   month_stats,
        "recent":    recent_list,
        "best5":     [fmt(t) for t in best5],
        "worst5":    [fmt(t) for t in worst5],
    }

    os.makedirs("data", exist_ok=True)
    with open("data/stats.json","w",encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, separators=(",",":"))

    print(f"\n  통계 항목:")
    print(f"  - 전체 / 순위별 / 요일별 / 점수대별 / 월별")
    print(f"  - 최근 30일 히스토리")
    print(f"  - 베스트 5 / 워스트 5")
    print(f"\n✅ data/stats.json 저장 완료!\n")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        traceback.print_exc()
  
