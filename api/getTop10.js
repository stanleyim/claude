export default async function handler(req, res) {
  try {
    // ✔ GitHub raw 데이터 (Vercel에서 가장 안정적)
    const tracking = await fetch(
      "https://raw.githubusercontent.com/USER/REPO/main/data/tracking.json"
    ).then(r => r.json());

    const stats = await fetch(
      "https://raw.githubusercontent.com/USER/REPO/main/data/stats.json"
    ).then(r => r.json());

    // ✔ TOP10 생성
    const top10 = tracking
      .sort((a, b) => (b.score || 0) - (a.score || 0))
      .slice(0, 10)
      .map(item => ({
        symbol: item.code,
        name: item.name,
        score: item.score,
        return: item.finalReturn || 0,
        result: item.result
      }));

    // ✔ 최종 응답
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

    return res.status(200).json(response);

  } catch (e) {
    console.error("API ERROR:", e);
    return res.status(500).json({
      error: "data not ready"
    });
  }
}
