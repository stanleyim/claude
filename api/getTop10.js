import fs from "fs";
import path from "path";

export default function handler(req, res) {
  try {
    const trackingPath = path.join(process.cwd(), "data", "tracking.json");
    const statsPath = path.join(process.cwd(), "data", "stats.json");

    const tracking = JSON.parse(
      fs.readFileSync(trackingPath, "utf-8")
    );

    const stats = JSON.parse(
      fs.readFileSync(statsPath, "utf-8")
    );

    const top10 = tracking
      .sort((a, b) => b.score - a.score)
      .slice(0, 10)
      .map(item => ({
        symbol: item.code,
        name: item.name,
        score: item.score,
        return: item.finalReturn || 0,
        result: item.result
      }));

    const response = {
      accuracy: stats.accuracy || 0,
      validated_count: stats.validated_count || 0,
      analyzed_count: stats.analyzed_count || 0,
      top10,
      factor_scores: stats.factor_scores || {
        momentum: 0,
        volume: 0
      },
      signal: stats.signal || "HOLD"
    };

    res.status(200).json(response);

  } catch (e) {
    console.error(e); // 👈 로그 확인용
    res.status(500).json({
      error: "data not ready"
    });
  }
    }
