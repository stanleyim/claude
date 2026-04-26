// ════════════════════════════════
// 설정
// ════════════════════════════════
const API_URL = "https://claude-ckuv.vercel.app/api/getTop10";
const TRACKING_URL = "https://claude-ckuv.vercel.app/api/tracking";
const STATS_URL    = "https://claude-ckuv.vercel.app/api/stats";

function $(id){ return document.getElementById(id); }
function setText(id, val){ const el=$(id); if(el) el.textContent=val; }

// ════════════════════════════════
// 에러 메시지
// ════════════════════════════════
const ERROR_MSG = {
  network: "🌐 네트워크 오류",
  http:    "🚫 서버 오류",
  parse:   "📄 데이터 오류",
  empty:   "📭 데이터 없음",
  unknown: "⚠ 알 수 없는 오류"
};

// ════════════════════════════════
// TOP10 로드
// ════════════════════════════════
async function loadData(){
  try{
    const res = await fetch(API_URL, { cache:"no-store" });
    if(!res.ok) return { error:true, reason:"http" };

    const j = await res.json();

    const list = j.top10 || [];
    if(list.length === 0){
      return { error:true, reason:"empty" };
    }

    return {
      stocks: list.map((s,i)=>({
        rank: i+1,
        code: s.symbol || "",
        name: s.name || "N/A",
        score: s.score || 0
      })),
      analyzed: j.analyzed_count || 0,
      accuracy: j.accuracy || 0,
      validated: j.validated_count || 0
    };

  }catch(e){
    console.error(e);
    return { error:true, reason:"network" };
  }
}

// ════════════════════════════════
// tracking
// ════════════════════════════════
async function loadTracking(){
  try{
    const res = await fetch(TRACKING_URL);
    if(!res.ok) return null;
    return await res.json();
  }catch(e){
    console.error("tracking error", e);
    return null;
  }
}

// ════════════════════════════════
// stats
// ════════════════════════════════
async function loadStats(){
  try{
    const res = await fetch(STATS_URL);
    if(!res.ok) return null;
    return await res.json();
  }catch(e){
    console.error("stats error", e);
    return null;
  }
}

// ════════════════════════════════
// 렌더링
// ════════════════════════════════
function render(data){
  const loading = $("loading");
  if(loading) loading.style.display = "none";

  if(data.error){
    $("grid").innerHTML =
      `<div style="padding:20px;color:#ff5555;">
        ${ERROR_MSG[data.reason] || ERROR_MSG.unknown}
      </div>`;
    return;
  }

  setText("hitRate", data.accuracy + "%");
  setText("totalPicks", data.validated + "건");
  setText("totalAnalyzed", data.analyzed + "종목");

  const grid = $("grid");

  grid.innerHTML = data.stocks.map(s => `
    <div style="padding:12px;border:1px solid #eee;margin:6px;border-radius:8px;">
      <div style="font-weight:700">${s.rank}. ${s.name}</div>
      <div style="font-size:12px;color:#888">${s.code}</div>
      <div style="font-size:18px;margin-top:6px;">점수: ${s.score}</div>
    </div>
  `).join("");
}

// ════════════════════════════════
// 날짜
// ════════════════════════════════
function setDate(){
  const el = $("hdate");
  if(!el) return;

  el.textContent = new Date().toLocaleDateString("ko-KR", {
    year:"numeric", month:"long", day:"numeric", weekday:"short"
  });
}

// ════════════════════════════════
// 시작
// ════════════════════════════════
async function init(){
  console.log("🚀 INIT");

  setDate();

  const data = await loadData();
  render(data);

  // 🔥 추가 연결 (핵심)
  const tracking = await loadTracking();
  const stats = await loadStats();

  console.log("TRACKING:", tracking);
  console.log("STATS:", stats);

  // 👉 여기서 UI 확장 가능 (차트/성과박스)
}

init();
