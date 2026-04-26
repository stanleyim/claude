export default async function handler(req, res) {
  try {

    // ✅ 실제 TOP10 데이터
    const stocksData = await fetch(
      "https://raw.githubusercontent.com/stanleyim/claude/main/data/daily_stocks.json"
    ).then(r => r.json());

    // ✅ 통계
    const statsData = await fetch(
      "https://raw.githubusercontent.com/stanleyim/claude/main/data/stats.json"
    ).then(r => r.json());

    const top10 = (stocksData.stocks || [])
      .sort((a,b) => (b.score?.total || 0) - (a.score?.total || 0))
      .slice(0,10)
      .map(s => ({
        symbol: s.code,
        name: s.name,
        score: s.score?.total || 0,
        return: 0,
        result: "pending"
      }));

    res.status(200).json({
      accuracy: statsData?.overall?.accuracy || 0,
      validated_count: statsData?.overall?.total || 0,
      analyzed_count: stocksData?.totalAnalyzed || 0,
      top10
    });

  } catch (e) {
    res.status(500).json({ error: e.message });
  }
}
