// ════════════════════════════════
// 상수
// ════════════════════════════════
const FL = ['수급','모멘텀','거래량','재무','변동성','뉴스','공매도','섹터'];
const FK = ['supply','momentum','volume','fundamental','volatility','news','shortSell','sector'];

let stocks = [];
let radarC = null;
let barC = null;

// ════════════════════════════════
// 안전 DOM
// ════════════════════════════════
const el = (id) => document.getElementById(id);

// ════════════════════════════════
// 데이터 로드 (API 단일)
// ════════════════════════════════
async function loadData(){
  try{
    const r = await fetch('/api/getTop10?t=' + Date.now());
    if(!r.ok) throw new Error('API error');

    const j = await r.json();

    if(!j.top10 || !Array.isArray(j.top10)) return null;

    return {
      stocks: j.top10.map((s,i)=>({
        rank:i+1,
        code:s.symbol,
        name:s.name,
        score:{
          total:s.score||0,
          breakdown:{
            supply:0,momentum:0,volume:0,fundamental:0,
            volatility:0,news:0,shortSell:0,sector:0
          }
        }
      })),
      date:new Date().toISOString().split('T')[0],
      totalAnalyzed:j.analyzed_count||0,
      hitStats:{
        hitRate:j.accuracy||0,
        totalPicks:j.validated_count||0,
        avgReturn:0
      }
    };

  }catch(e){
    console.error("loadData error:",e);
    return null;
  }
}

// ════════════════════════════════
// 휴장 표시
// ════════════════════════════════
function showHoliday(msg){
  if(el('loading')) el('loading').style.display='none';

  if(el('hdate')) el('hdate').textContent = msg;
  if(el('aiText')) el('aiText').textContent = msg;

  if(el('grid')){
    el('grid').innerHTML = `
      <div style="padding:20px;color:#888;">
        ${msg}
      </div>`;
  }
}

// ════════════════════════════════
// 성과
// ════════════════════════════════
function renderPerf(hitStats,total){
  if(!el('hitRate')) return;

  el('hitRate').textContent =
    hitStats?.totalPicks ? `${hitStats.hitRate}%` : '--';

  el('totalPicks').textContent =
    hitStats?.totalPicks ? `${hitStats.totalPicks}건` : '--';

  el('avgReturn').textContent =
    hitStats?.avgReturn ? `${hitStats.avgReturn}%` : '--';

  el('totalAnalyzed').textContent =
    (total||0) + '종목';
}

// ════════════════════════════════
// 카드
// ════════════════════════════════
function renderCards(list){
  if(!el('grid')) return;

  el('grid').innerHTML = list.map(s=>`
    <div class="card">
      <div>${s.name}</div>
      <div>${s.code}</div>
      <div>${s.score?.total||0}</div>
    </div>
  `).join('');
}

// ════════════════════════════════
// 차트 (완전 안전)
// ════════════════════════════════
function renderCharts(list){

  if(!window.Chart){
    console.log("Chart.js not loaded");
    return;
  }

  const radarEl = el('radar');
  const barEl = el('barC');

  if(!radarEl || !barEl){
    console.log("Chart DOM missing");
    return;
  }

  const avg = arr => arr.reduce((a,b)=>a+b,0)/Math.max(arr.length,1);

  const radarData = FK.map(()=>0);

  try{
    if(radarC) radarC.destroy();
    radarC = new Chart(radarEl.getContext('2d'),{
      type:'radar',
      data:{
        labels:FL,
        datasets:[{
          data:radarData,
          borderColor:'#3b82f6'
        }]
      },
      options:{responsive:true,maintainAspectRatio:false}
    });
  }catch(e){
    console.log("radar error",e);
  }

  try{
    if(barC) barC.destroy();
    barC = new Chart(barEl.getContext('2d'),{
      type:'bar',
      data:{
        labels:list.map(s=>s.name),
        datasets:[{
          data:list.map(s=>s.score?.total||0),
          backgroundColor:'#3b82f6'
        }]
      },
      options:{responsive:true,maintainAspectRatio:false}
    });
  }catch(e){
    console.log("bar error",e);
  }
}

// ════════════════════════════════
// INIT
// ════════════════════════════════
async function init(){

  console.log("INIT START");

  const day = new Date().getDay();
  if(day===0||day===6){
    showHoliday("주말 — 휴장");
    return;
  }

  const data = await loadData();

  if(el('loading')) el('loading').style.display='none';

  if(!data){
    if(el('aiText'))
      el('aiText').textContent = "데이터 없음 (API 확인 필요)";
    return;
  }

  stocks = data.stocks || [];

  console.log("DATA OK", stocks);

  if(el('hdate')) el('hdate').textContent = data.date;

  renderPerf(data.hitStats, data.totalAnalyzed);
  renderCards(stocks);
  renderCharts(stocks);
}

init();
