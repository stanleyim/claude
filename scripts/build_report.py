import json
import os
from datetime import datetime

DATA_DIR = "data"

def build_report():
    # tracking.json 읽기
    tracking_path = os.path.join(DATA_DIR, "tracking.json")
    tracking = []
    if os.path.exists(tracking_path):
        with open(tracking_path, "r", encoding="utf-8") as f:
            tracking = json.load(f)

    # stats.json 읽기  
    stats_path = os.path.join(DATA_DIR, "stats.json")
    stats = {}
    if os.path.exists(stats_path):
        with open(stats_path, "r", encoding="utf-8") as f:
            stats = json.load(f)

    # report.json 생성
    report = {
        "title": "Daily Stock Report",
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "summary": f"전체 적중률: {stats.get('hit_rate', 0)}%, 평균 수익률: {stats.get('avg_return', 0)}%",
        "data": tracking[-10:]  # 최근 10건만
    }

    with open(os.path.join(DATA_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"✅ report.json 생성 완료 - {len(report['data'])}건")

if __name__ == "__main__":
    build_report()
