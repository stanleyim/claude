// ════════════════════════════════
// 설정
// ════════════════════════════════
const API_URL = "https://claude-ckuv.vercel.app/api/getTop10";

// 안전 DOM 접근
function $(id){
  return document.getElementById(id);
}

// 안전 텍스트 설정
function setText(id, val){
  const el = $(id);
  if(el) el.textContent = val;
}

// ════════════════════════════════
// 데이터 로드 (절대 멈추지 않음)
// ════════════════════════════════
async function loadData(){
  try{
    const controller = new AbortController();
    const timeout = setTimeout(()=>controller.abort(), 5000);

    const res = await fetch(API_URL + "?t=" + Date.now(), {
      signal: controller.signal,
      cache: "no-store"
    });

    clearTimeout(timeout);

    if(!res.ok) throw new Error("API ERROR");

    const j = await res.json();
    console.log("API OK:", j);

    return {
      stocks: (j.top10 || []).map((s,i)=>({
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
    console.error("❌ API 실패:", e);

    return {
      stocks: [],
      analyzed: 0,
      accuracy: 0,
      validated: 0
    };
  }
}

// ════════════════════════════════
// 렌더링 (절대 에러 안 남)
// ════════════════════════════════
function render(data){

  // 로딩 제거
  const loading = $("loading");
  if(loading) loading.style.display = "none";

  // 상단
  setText("hitRate", data.validated ? data.accuracy + "%" : "--");
  setText("totalPicks", data.validated ? data.validated + "건" : "--");
  setText("totalAnalyzed", data.analyzed + "종목");
  setText("avgReturn", "--");

  // 카드
  const grid = $("grid");
  if(!grid) return;

  if(!data.stocks.length){
    grid.innerHTML = `
      <div style="padding:20px;color:#999;">
        ⚠ 데이터 없음 (API 대기 또는 오류)
      </div>
    `;
    return;
  }

  grid.innerHTML = data.stocks.map(s=>`
    <div style="padding:12px;border:1px solid #eee;margin:6px;border-radius:8px;">
      <div style="font-weight:700">${s.rank}. ${s.name}</div>
      <div style="font-size:12px;color:#888">${s.code}</div>
      <div style="font-size:18px;margin-top:6px;">점수: ${s.score}</div>
    </div>
  `).join("");
}

// ════════════════════════════════
// 시작
// ════════════════════════════════
async function init(){
  console.log("🚀 INIT 시작");

  const data = await loadData();

  console.log("📦 데이터 수신 완료");

  render(data);
}

// 실행
init();
