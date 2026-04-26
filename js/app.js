// ════════════════════════════════
// 상수
// ════════════════════════════════
const API_URL = "https://claude-ckuv.vercel.app/api/getTop10";

let stocks = [];
let radarC = null;
let barC = null;

// ════════════════════════════════
// 데이터 로드 (타임아웃 + 무한로딩 방지)
// ════════════════════════════════
async function loadData() {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const res = await fetch(API_URL + "?t=" + Date.now(), {
      signal: controller.signal,
      cache: "no-store"
    });

    clearTimeout(timeout);

    if (!res.ok) throw new Error("API ERROR");

    const j = await res.json();
    console.log("API DATA:", j);

    const list = (j.top10 || []).map((s, i) => ({
      rank: i + 1,
      code: s.symbol || "",
      name: s.name || "N/A",
      score: s.score || 0
    }));

    return {
      stocks: list,
      analyzed: j.analyzed_count || 0,
      accuracy: j.accuracy || 0,
      validated: j.validated_count || 0
    };

  } catch (e) {
    console.error("❌ fetch 실패:", e);

    // 🔥 실패해도 화면은 반드시 뜨게
    return {
      stocks: [],
      analyzed: 0,
      accuracy: 0,
      validated: 0
    };
  }
}

// ════════════════════════════════
// 렌더링
// ════════════════════════════════
function render(data) {

  document.getElementById("loading").style.display = "none";

  // 상단 정보
  document.getElementById("hitRate").textContent =
    data.validated ? data.accuracy + "%" : "--";

  document.getElementById("totalPicks").textContent =
    data.validated ? data.validated + "건" : "--";

  document.getElementById("totalAnalyzed").textContent =
    data.analyzed + "종목";

  document.getElementById("avgReturn").textContent = "--";

  // 카드
  const grid = document.getElementById("grid");

  if (!data.stocks.length) {
    grid.innerHTML = `
      <div style="padding:20px;color:#999;">
        데이터
