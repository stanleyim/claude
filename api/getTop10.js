import fs from "fs";

export default function handler(req, res) {
  try {
    const tracking = JSON.parse(
      fs.readFileSync("./data/tracking.json", "utf-8")
    );

    const stats = JSON.parse(
      fs.readFileSync("./data/stats.json", "utf-8")
    );

    // ✔ 핵심 수정: code/name 기반
    const top10 = tracking
      .sort((a, b) => b.score - a.score)
      .slice(0, 10)
      .map(item => ({
        symbol: item.code,   // ✔ 핵심 수정
        name: item.name,
        score: item.score,
        return: item.finalReturn || 0,
        result: item.result
      }));

    const factor_scores = stats.factor_scores || {
      momentum: 0,
      volume: 0
    };

    const response = {
      accuracy: stats.accuracy || 0,
      validated_count: stats.validated_count || 0,
      analyzed_count: stats.analyzed_count || 0,
      top10,
      factor_scores,
      signal: stats.signal || "HOLD"
    };

    res.status(200).json(response);

  } catch (e) {
    res.status(500).json({
      error: "data not ready"
    });
  }
}
