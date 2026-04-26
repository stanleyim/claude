import json
from datetime import datetime

def build_report():
    report = {
        "title": "Daily Stock Report",
        "generatedAt": datetime.utcnow().isoformat(),
        "summary": "Auto generated report from pipeline",
        "data": []
    }

    with open("data/report.json", "w") as f:
        json.dump(report, f, indent=2)

if __name__ == "__main__":
    build_report()
