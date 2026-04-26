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
// 데이터 로드 (안정화 버전)
// ════════════════════════════════
async function loadData(){
  try{

    const res = await fetch(API_URL + "?t=" + Date.now(), {
      cache: "no-store"
    });

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
      stocks: null,
      analyzed: 0,
      accuracy: 0,
      validated: 0,
      error: true
    };
  }
}

// ════════════════════════════════
// 렌더링 (안정 버전)
// ════════════════════════════════
function render(data){

  const loading = $("loading");
  if(loading) loading.style.display = "none";

  // API 실패 처리
  if(data.error){
    const grid = $("grid");
    if(grid){
      grid.innerHTML = `
        <div style="padding:20px;color:#ff5555;">
          ⚠ API 연결 실패
        </div>
      `;
    }
    return;
  }

  // 상단
  setText("hitRate", data.validated ? data.accuracy + "%" : "--");
  setText("totalPicks", data.validated ? data.validated + "건" : "--");
  setText("totalAnalyzed", data.analyzed + "종목");
  setText("avgReturn", "--");

  const grid = $("grid");
  if(!grid) return;

  // 데이터 체크
  if(!data.stocks || data.stocks.length === 0){
    grid.innerHTML = `
      <div style="padding:20px;color:#999;">
        ⚠ 데이터 없음
      </div>
    `;
    return;
  }

  // 카드 렌더링
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

  console.log("📦 데이터 수신 완료", data);

  render(data);
}

// 실행
init();
