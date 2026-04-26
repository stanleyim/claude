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
    // 🔥 여기에 실제 데이터 로직 연결
    // (예: DB / 파일 / AI 결과 / 스크래핑 등)
    // ════════════════════════════════

    const rawData = await getTop10Data(); 
    // ↑ 너 기존 로직 여기 연결

    // 데이터 안전성 보장
    const safeData = {
      top10: Array.isArray(rawData?.top10) ? rawData.top10 : [],
      analyzed_count: rawData?.analyzed_count ?? 0,
      accuracy: rawData?.accuracy ?? 0,
      validated_count: rawData?.validated_count ?? 0
    };

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
