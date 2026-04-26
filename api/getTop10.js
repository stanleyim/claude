export default async function handler(req, res) {

  // ════════════════════════════════
  // CORS (필수)
  // ════════════════════════════════
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  // preflight 대응
  if (req.method === "OPTIONS") {
    return res.status(200).end();
  }

  try {

    // ════════════════════════════════
    // 🔥 실제 데이터 로직 연결
    // 여기만 너 기존 코드 붙이면 됨
    // ════════════════════════════════
    const rawData = await getTop10Data(); 
    // ↑ 이 함수는 너가 이미 쓰던 로직 그대로

    // ════════════════════════════════
    // 안전 처리 (중요)
    // ════════════════════════════════
    const safeData = {
      top10: Array.isArray(rawData?.top10) ? rawData.top10 : [],
      analyzed_count: rawData?.analyzed_count ?? 0,
      accuracy: rawData?.accuracy ?? 0,
      validated_count: rawData?.validated_count ?? 0
    };

    // empty 방지 로그
    if (!safeData.top10.length) {
      console.warn("⚠️ TOP10 EMPTY");
    }

    // ════════════════════════════════
    // 응답
    // ════════════════════════════════
    return res.status(200).json(safeData);

  } catch (e) {

    console.error("❌ getTop10 ERROR:", e);

    return res.status(500).json({
      error: "INTERNAL_SERVER_ERROR",
      message: e.message || "unknown error",
      top10: [],
      analyzed_count: 0,
      accuracy: 0,
      validated_count: 0
    });
  }
}
