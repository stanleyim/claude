// ════════════════════════════════
// 설정
// ════════════════════════════════
const API_URL = "https://claude-ckuv.vercel.app/api/getTop10";

function $(id){ return document.getElementById(id); }
function setText(id, val){ const el=$(id); if(el) el.textContent=val; }

// ════════════════════════════════
// 에러 메시지 매핑
// ════════════════════════════════
const ERROR_MSG = {
  network: "🌐 네트워크 오류 — 인터넷 연결을 확인하세요",
  http:    "🚫 서버 오류 — 잠시 후 다시 시도하세요",
  parse:   "📄 데이터 형식 오류 — API 응답이 예상과 다릅니다",
  empty:   "📭 데이터 없음 — 오늘의 추천 종목이 아직 없습니다",
  unknown: "⚠ 알 수 없는 오류 — 콘솔을 확인하세요"
};

// ════════════════════════════════
// 데이터 로드
// ════════════════════════════════
async function loadData(){
  try{

    let res;
    try{
      res = await fetch(API_URL, { cache:"no-store" });
    }catch(e){
      // fetch() 자체 실패 = 네트워크 단절 / CORS
      console.error("❌ NETWORK ERROR:", e.message);
      return { stocks:[], error:true, reason:"network" };
    }

    if(!res.ok){
      console.error("❌ HTTP ERROR:", res.status);
      return { stocks:[], error:true, reason:"http", status:res.status };
    }

    let j;
    try{
      j = await res.json();
    }catch(e){
      console.error("❌ PARSE ERROR:", e.message);
      return { stocks:[], error:true, reason:"parse" };
    }

    console.log("✅ API OK:", j);

    const list = j.top10 || [];
    if(list.length === 0){
      return { stocks:[], error:true, reason:"empty",
               analyzed:j.analyzed_count||0, accuracy:j.accuracy||0, validated:j.validated_count||0 };
    }

    return {
      stocks: list.map((s,i)=>({
        rank:  i+1,
        code:  s.symbol || "",
        name:  s.name   || "N/A",
        score: s.score  || 0
      })),
      analyzed:  j.analyzed_count  || 0,
      accuracy:  j.accuracy        || 0,
      validated: j.validated_count || 0
    };

  }catch(e){
    console.error("❌ UNKNOWN ERROR:", e.message);
    return { stocks:[], error:true, reason:"unknown" };
  }
}

// ════════════════════════════════
// 렌더링 — 절대 안전 모드
// ════════════════════════════════
function render(data){
  try{

    const loading = $("loading");
    if(loading) loading.style.display = "none";

    if(data.error){
      const msg  = ERROR_MSG[data.reason] || ERROR_MSG.unknown;
      const sub  = data.status ? ` (HTTP ${data.status})` : "";
      const grid = $("grid");
      if(grid) grid.innerHTML = `
        <div style="padding:20px 16px;color:#ff5555;line-height:1.7;">
          ${msg}${sub}
        </div>`;
      return;
    }

    setText("hitRate",       data.validated ? data.accuracy  + "%" : "--");
    setText("totalPicks",    data.validated ? data.validated + "건" : "--");
    setText("totalAnalyzed", data.analyzed  ? data.analyzed  + "종목" : "--");
    setText("avgReturn",     "--");

    const grid = $("grid");
    if(!grid) return;

    grid.innerHTML = (data.stocks || []).map(s=>`
      <div style="padding:12px;border:1px solid #eee;margin:6px;border-radius:8px;">
        <div style="font-weight:700">${s.rank}. ${s.name}</div>
        <div style="font-size:12px;color:#888">${s.code}</div>
        <div style="font-size:18px;margin-top:6px;">점수: ${s.score}</div>
      </div>
    `).join("");

  }catch(e){
    console.error("❌ RENDER ERROR:", e.message);
  }
}

// ════════════════════════════════
// 탭 / 날짜 / 모달
// ════════════════════════════════
function switchTab(tab){
  try{
    const tabs   = document.querySelectorAll(".ptab");
    const recent = $("tabRecent");
    const stats  = $("tabStats");
    tabs.forEach(t=>t.classList.remove("active"));
    if(tab==="recent"){
      if(tabs[0]) tabs[0].classList.add("active");
      if(recent)  recent.style.display = "";
      if(stats)   stats.style.display  = "none";
    } else {
      if(tabs[1]) tabs[1].classList.add("active");
      if(recent)  recent.style.display = "none";
      if(stats)   stats.style.display  = "";
    }
  }catch(e){ console.error("TAB ERROR:", e.message); }
}

function setDate(){
  try{
    const el = $("hdate");
    if(!el) return;
    el.textContent = new Date().toLocaleDateString("ko-KR",{
      year:"numeric", month:"long", day:"numeric", weekday:"short"
    });
  }catch(e){ console.error("DATE ERROR:", e.message); }
}

function closeM(e){
  try{
    if(!e || e.target===$("moverlay")){
      const o=$("moverlay"); if(o) o.style.display="none";
    }
  }catch(e){ console.error("MODAL ERROR:", e.message); }
}

// ════════════════════════════════
// 시작
// ════════════════════════════════
async function init(){
  try{
    console.log("🚀 INIT");
    setDate();
    const data = await loadData();
    render(data);
  }catch(e){
    console.error("❌ INIT ERROR:", e.message);
  }
}

init();
