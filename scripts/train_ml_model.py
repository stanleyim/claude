# -*- coding: utf-8 -*-
"""
ML 모델 학습 엔진 (XGBoost)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tracking.json 에서 과거 추천 데이터 로드
→ 피처 추출 → XGBoost 학습
→ data/ml_model.json (가중치/파라미터) 저장
→ fetch_daily_data.py 가 자동으로 로드해서 사용

데이터 부족 시 (30건 미만):
→ 기본 룰 기반 가중치 사용
"""

import json, os, datetime, traceback
import numpy as np

# ── 피처 추출 ──────────────────────────────────
def extract_features(stock):
    """
    종목 데이터에서 ML 피처 추출
    """
    bd = stock.get("score", {}).get("breakdown", {})
    return [
        bd.get("supply",    50),   # 수급 점수
        bd.get("momentum",  50),   # 모멘텀 점수
        bd.get("volume",    50),   # 거래량 점수
        bd.get("short",     50),   # 단기수익 점수
        bd.get("news",      50),   # 뉴스 점수
        bd.get("shortSell", 50),   # 공매도 점수
        stock.get("score", {}).get("total", 50),  # 종합 점수
        stock.get("rank", 5),      # 순위
    ]

FEATURE_NAMES = [
    "supply", "momentum", "volume", "short",
    "news", "shortSell", "total", "rank"
]

# ── 메인 ──────────────────────────────────────
def main():
    today = datetime.date.today()
    print(f"\n{'='*52}")
    print(f"  🤖 ML 모델 학습 — {today}")
    print(f"{'='*52}\n")

    # tracking.json 로드
    tracking_path = "data/tracking.json"
    if not os.path.exists(tracking_path):
        print("  ⚠️ tracking.json 없음 → 룰 기반 사용")
        save_default_weights()
        return

    try:
        with open(tracking_path, encoding="utf-8") as f:
            tracking = json.load(f)
    except Exception as e:
        print(f"  ⚠️ 로드 오류: {e} → 룰 기반 사용")
        save_default_weights()
        return

    # 완료된 데이터만
    done = [t for t in tracking if t.get("result") in ["hit", "miss"]]
    print(f"  학습 데이터: {len(done)}건")

    # 최소 30건 필요
    if len(done) < 30:
        print(f"  ⚠️ 데이터 부족 ({len(done)}건 < 30건) → 룰 기반 사용")
        save_default_weights()
        return

    # 피처 / 레이블 준비
    X, y = [], []
    for t in done:
        try:
            features = [
                t.get("breakdown", {}).get("supply",    50),
                t.get("breakdown", {}).get("momentum",  50),
                t.get("breakdown", {}).get("volume",    50),
                t.get("breakdown", {}).get("short",     50),
                t.get("breakdown", {}).get("news",      50),
                t.get("breakdown", {}).get("shortSell", 50),
                t.get("score",  50),
                t.get("rank",    5),
            ]
            label = 1 if t.get("result") == "hit" else 0
            X.append(features)
            y.append(label)
        except: continue

    if len(X) < 30:
        print("  ⚠️ 유효 데이터 부족 → 룰 기반 사용")
        save_default_weights()
        return

    X = np.array(X)
    y = np.array(y)

    # XGBoost 학습
    try:
        import xgboost as xgb
        from sklearn.model_selection import cross_val_score

        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="logloss",
            use_label_encoder=False,
        )
        model.fit(X, y)

        # 교차검증 정확도
        scores = cross_val_score(model, X, y, cv=min(5, len(X)//6+1), scoring="accuracy")
        accuracy = round(scores.mean() * 100, 1)
        print(f"  ✅ XGBoost 학습 완료")
        print(f"  교차검증 정확도: {accuracy}%")

        # 피처 중요도 → 가중치로 변환
        importance = model.feature_importances_
        total_imp   = sum(importance)
        weights = {
            FEATURE_NAMES[i]: round(float(importance[i]) / total_imp, 3)
            for i in range(len(FEATURE_NAMES))
        }
        print(f"  피처 중요도: {weights}")

        # 모델 파라미터 저장 (joblib 대신 JSON)
        booster_params = model.get_booster().save_raw("json").decode("utf-8")

        output = {
            "trainedAt":  str(today),
            "dataCount":  len(X),
            "accuracy":   accuracy,
            "weights":    weights,
            "useML":      True,
            "booster":    booster_params,
        }

    except Exception as e:
        print(f"  ⚠️ XGBoost 오류: {e}")
        print(f"  → 피처 중요도 기반 가중치만 저장")

        # XGBoost 실패해도 상관관계 기반 가중치 계산
        X_arr = np.array(X)
        y_arr = np.array(y)
        correlations = [abs(np.corrcoef(X_arr[:, i], y_arr)[0, 1])
                        for i in range(X_arr.shape[1])]
        total = sum(correlations) or 1
        weights = {
            FEATURE_NAMES[i]: round(correlations[i] / total, 3)
            for i in range(len(FEATURE_NAMES))
        }
        output = {
            "trainedAt": str(today),
            "dataCount": len(X),
            "accuracy":  0,
            "weights":   weights,
            "useML":     False,
        }

    os.makedirs("data", exist_ok=True)
    with open("data/ml_model.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  → data/ml_model.json 저장 완료\n")
    print("✅ ML 모델 학습 완료!\n")

def save_default_weights():
    """기본 룰 기반 가중치 저장"""
    output = {
        "trainedAt": str(datetime.date.today()),
        "dataCount": 0,
        "accuracy":  0,
        "weights": {
            "supply":    0.35,
            "momentum":  0.25,
            "volume":    0.18,
            "short":     0.12,
            "news":      0.05,
            "shortSell": 0.05,
        },
        "useML": False,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/ml_model.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("  → 기본 가중치 저장 완료\n")

if __name__ == "__main__":
    try: main()
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        traceback.print_exc()
        save_default_weights()
  
