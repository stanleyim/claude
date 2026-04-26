// ════════════════════════════════
// 상수
// ════════════════════════════════
const FL = ['수급','모멘텀','거래량','재무','변동성','뉴스','공매도','섹터'];
const FK = ['supply','momentum','volume','fundamental','volatility','news','shortSell','sector'];

let stocks=[], radarC=null, barC=null;

// ════════════════════════════════
// 데이터 로드 (API 기준)
// ════════════════════════════════
async function loadData(){
  try{
    const r = await fetch('/api/getTop10?t=' + Date.now());
    if(!r.ok) throw new Error('api error');

    const j = await r.json();
    console.log("API DATA:", j);

    const stocks = (j.top10 || []).map((s, i) => ({
      rank: i + 1,
      code: s.symbol || '',
      name: s.name || 'N/A',
      price: 0,
      changeRate: 0,
      sector: '',
      market: '',
      score: {
        total: s.score || 0,
        reasons: [],
        risk: '',
        breakdown: {
          supply: 0,
          momentum: 0,
          volume: 0,
          fundamental: 0,
          volatility: 0,
          news: 0,
          shortSell: 0,
          sector: 0
        }
      }
    }));

    return {
      stocks,
      date: new Date().toISOString().split('T')[0],
      totalAnalyzed: j.analyzed_count || 0,
      hitStats: {
        hitRate: j.accuracy || 0,
        totalPicks: j.validated_count || 0,
        avgReturn: 0
      }
    };

  }catch(e){
    console.error("loadData error:", e);
    return null;
  }
}

// ════════════════════════════════
// 성과 표시
// ════════════════════════════════
function renderPerf(hitStats, totalAnalyzed){
  document.getElementById('hitRate').textContent =
    hitStats.totalPicks > 0 ? hitStats.hitRate + '%' : '--';

  document.getElementById('totalPicks').textContent =
    hitStats.totalPicks > 0 ? hitStats.totalPicks + '건' : '--';

  document.getElementById('avgReturn').textContent =
    hitStats.totalPicks > 0 ? hitStats.avgReturn + '%' : '--';

  document.getElementById('totalAnalyzed').textContent =
    (totalAnalyzed || 0) + '종목';
}

// ════════════════════════════════
// 카드 렌더
// ════════════════════════════════
function renderCards(list){
  document.getElementById('grid').innerHTML = list.map((s,i)=>`
    <div class="card">
      <div class="name-block">
        <div class="sname">${i+1}. ${s.name}</div>
        <div class="smeta">${s.code}</div>
      </div>
      <div class="score-ring">
        <div class="snum">${s.score.total}</div>
      </div>
    </div>
  `).join('');
}

// ════════════════════════════════
// 차트
// ════════════════════════════════
function renderCharts(list){
  const avg = arr => arr.reduce((a,b)=>a+b,0)/Math.max(arr.length,1);

  if(radarC) radarC.destroy();
  radarC = new Chart(document.getElementById('radar'), {
    type:'radar',
    data:{
      labels:FL,
      datasets:[{
        data:FK.map(k => Math.round(avg(list.map(s => s.score.breakdown[k] || 0)))),
        borderColor:'#3b82f6'
      }]
    },
    options:{responsive:true, maintainAspectRatio:false}
  });

  if(barC) barC.destroy();
  barC = new Chart(document.getElementById('barC'), {
    type:'bar',
    data:{
      labels:list.map(s=>s.name),
      datasets:[{
        data:list.map(s=>s.score.total),
        backgroundColor:'#3b82f6'
      }]
    },
    options:{responsive:true, maintainAspectRatio:false}
  });
}

// ════════════════════════════════
// 메인 초기화
// ════════════════════════════════
async function init(){

  const today = new Date();
  const day = today.getDay();
  const todayStr = today.toISOString().split('T')[0];

  const data = await loadData();

  document.getElementById('loading').style.display='none';

  // ❌ 데이터 없을 때
  if(!data){
    document.getElementById('aiText').textContent =
      '데이터 없음 (API 확인 필요)';
    return;
  }

  // 🔥 상태 표시
  if(day === 0 || day === 6){
    document.getElementById('liveBadge').textContent = '● 휴장';
    document.getElementById('aiText').textContent =
      '주말 — 최근 데이터 기준';
  }
  else if(data.date !== todayStr){
    document.getElementById('liveBadge').textContent = '● 휴장';
    document.getElementById('aiText').textContent =
      '최근 데이터 기준';
  }
  else{
    document.getElementById('liveBadge').textContent = '● LIVE';
  }

  stocks = data.stocks;

  document.getElementById('hdate').textContent = data.date;

  renderPerf(data.hitStats, data.totalAnalyzed);
  renderCards(stocks);
  renderCharts(stocks);
}

init();
