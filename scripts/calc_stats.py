# -*- coding: utf-8 -*-
"""
통계 자동 계산 엔진 (FIXED)
- tracking.json 구조 불일치 문제 해결
- result 필터 제거
- finalReturn 기반 통계 계산
"""

import json, os, datetime, traceback
from collections import defaultdict

TRACKING_PATH = "data/tracking.json"
OUTPUT_PATH = "data/stats.json"


def load_tracking():
    try:
        with open(TRACKING_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []


def avg(arr):
    return round(sum(arr) / len(arr), 2) if arr else 0


def hit_rate(arr):
    if not arr:
        return 0
    return round(len([x for x in arr if x > 0]) / len(arr) * 100, 1)


def main():
    today = datetime.date.today()

    print("\n" + "=" * 52)
    print(f"  📈 통계 계산 — {today}")
    print("=" * 52 + "\n")

    tracking = load_tracking()

    # ✅ FIX: result 의존 제거 (핵심 수정)
    done = [
        t for t in tracking
        if isinstance(t.get("finalReturn"), (int, float))
    ]

    # ─────────────────────────────
    # 0. 데이터 없음 처리
    # ─────────────────────────────
    if not done:
        print("  ⚠️ 완료된 데이터 없음 — 아직 통계 없음")

        output = {
            "updatedAt": str(today),
            "hasData": False,
            "totalTrades": 0,
            "hitRate": 0,
            "avgReturn": 0,
            "message": "데이터 축적 중입니다."
        }

        os.makedirs("data", exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        return

    returns = [t["finalReturn"] for t in done]

    # ─────────────────────────────
    # 1. 전체 통계
    # ─────────────────────────────
    overall = {
        "totalTrades": len(done),
        "hits": len([t for t in done if t["finalReturn"] > 0]),
        "hitRate": hit_rate(returns),
        "avgReturn": avg(returns),
        "bestReturn": round(max(returns), 2),
        "worstReturn": round(min(returns), 2),
    }

    print(f"  전체 적중률: {overall['hitRate']}%")
    print(f"  평균 수익률: {overall['avgReturn']}%")

    # ─────────────────────────────
    # 2. 순위별
    # ─────────────────────────────
    by_rank = defaultdict(list)
    for t in done:
        by_rank[t.get("rank", 0)].append(t["finalReturn"])

    rank_stats = {
        f"{r}위": {
            "hitRate": hit_rate(v),
            "avgReturn": avg(v),
            "count": len(v),
        }
        for r, v in sorted(by_rank.items())
    }

    # ─────────────────────────────
    # 3. 요일별
    # ─────────────────────────────
    DAY = ["월", "화", "수", "목", "금", "토", "일"]
    by_day = defaultdict(list)

    for t in done:
        try:
            d = datetime.date.fromisoformat(t["entryDate"]).weekday()
            by_day[DAY[d]].append(t["finalReturn"])
        except:
            continue

    day_stats = {
        k: {
            "hitRate": hit_rate(v),
            "avgReturn": avg(v),
            "count": len(v),
        }
        for k, v in by_day.items()
    }

    # ─────────────────────────────
    # 4. 점수대
    # ─────────────────────────────
    score_buckets = defaultdict(list)

    for t in done:
        sc = t.get("score", 0)

        if sc >= 85:
            bucket = "85+"
        elif sc >= 80:
            bucket = "80-84"
        elif sc >= 75:
            bucket = "75-79"
        elif sc >= 70:
            bucket = "70-74"
        else:
            bucket = "<70"

        score_buckets[bucket].append(t["finalReturn"])

    score_stats = {
        k: {
            "hitRate": hit_rate(v),
            "avgReturn": avg(v),
            "count": len(v),
        }
        for k, v in score_buckets.items()
    }

    # ─────────────────────────────
    # 5. 최근 30개
    # ─────────────────────────────
    recent = sorted(done, key=lambda x: x["entryDate"], reverse=True)[:30]

    recent_list = [
        {
            "date": t["entryDate"],
            "rank": t.get("rank", 0),
            "name": t.get("name"),
            "code": t.get("code"),
            "entryPrice": t.get("entryPrice"),
            "finalReturn": t["finalReturn"],
        }
        for t in recent
    ]

    # ─────────────────────────────
    # 6. 저장
    # ─────────────────────────────
    output = {
        "updatedAt": str(today),
        "hasData": True,
        "overall": overall,
        "byRank": rank_stats,
        "byDay": day_stats,
        "byScore": score_stats,
        "recent": recent_list,
    }

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n  ✅ stats.json 생성 완료")
    print("  📊 전체 / 순위 / 요일 / 점수 / 최근 데이터")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("❌ 오류:", e)
        traceback.print_exc()
