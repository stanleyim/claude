// ════════════════════════════════
// 상수
// ════════════════════════════════
const FL = ['수급','모멘텀','거래량','재무','변동성','뉴스','공매도','섹터'];
const FK = ['supply','momentum','volume','fundamental','volatility','news','shortSell','sector'];
const FW = ['25%','20%','15%','13%','10%','8%','5%','4%'];

let stocks=[], mChart=null, radarC=null, barC=null;

// ════════════════════════════════
// 데이터 로드 (핵심: API 단일화)
// ════════════════════════════════
async function loadData(){
  try{
    const r = await fetch('/api/getTop10?t=' + Date.now());
    if(!r.ok) throw new Error('api error');

    const j = await r.json();

    if(!j.top10 || !j.top10.length) return null;

    return {
      stocks: j.top10.map((s, i) => ({
        rank: i + 1,
        code: s.symbol,
        name: s.name,
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
      })),
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
// 시장 상태 (휴장 표시용 fallback)
// ════════════════════════════════
async function checkMarketStatus(){
  try{
    const r = await fetch('/api/getTop10?t=' + Date.now());
    if(r.ok) return await r.json();
  }catch(e){}
  return null;
}

// ════════════════════════════════
// 휴장 화면
// ════════════════════════════════
function showHoliday(msg){
  document.getElementById('loading').style.display='none';
  document.getElementById('hdate').textContent=msg;
  document.getElementById('liveBadge').textContent='● 휴장';
  document.getElementById('aiText').textContent=msg;
  document.getElementById('aiSub').textContent='다음 거래일 자동 업데이트';

  document.getElementById('grid').innerHTML=`
    <div class="holiday-wrap">
      <div class="holiday-title">${msg}</div>
      <div class="holiday-sub">데이터 없음 (시장 휴장)</div>
    </div>`;
}

// ════════════════════════════════
// 성과 배너
// ════════════════════════════════
function renderPerf(hitStats, totalAnalyzed){
  const hr=hitStats?.hitRate||0;
  const tp=hitStats?.totalPicks||0;
  const ar=hitStats?.avgReturn||0;

  document.getElementById('hitRate').textContent = tp>0 ? `${hr}%` : '--';
  document.getElementById('totalPicks').textContent = tp>0 ? `${tp}건` : '--';
  document.getElementById('avgReturn').textContent = tp>0 ? `${ar}%` : '--';
  document.getElementById('totalAnalyzed').textContent = (totalAnalyzed||0)+'종목';
}

// ════════════════════════════════
// 카드 렌더
// ════════════════════════════════
function renderCards(list){
  document.getElementById('grid').innerHTML = list.map((s,i)=>`
    <div class="card">
      <div class="name-block">
        <div class="sname">${s.name}</div>
        <div class="smeta">${s.code}</div>
      </div>

      <div class="score-ring">
        <div class="snum">${s.score?.total||0}</div>
      </div>
    </div>
  `).join('');
}

// ════════════════════════════════
// 차트 (빈 데이터 방지)
// ════════════════════════════════
function renderCharts(list){
  const avg = arr => arr.reduce((a,b)=>a+b,0)/Math.max(arr.length,1);

  const radarData = FK.map(k =>
    Math.round(avg(list.map(s => s.score?.breakdown?.[k] || 0)))
  );

  if(radarC) radarC.destroy();
  radarC = new Chart(document.getElementById('radar'), {
    type:'radar',
    data:{
      labels:FL,
      datasets:[{
        data: radarData,
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
        data:list.map(s=>s.score?.total||0),
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

  const day = new Date().getDay();
  if(day===0 || day===6){
    showHoliday('주말 — 증시 휴장');
    return;
  }

  const data = await loadData();
  document.getElementById('loading').style.display='none';

  if(!data){
    document.getElementById('aiText').textContent =
      '데이터 생성 대기 중 (GitHub Actions 확인)';
    return;
  }

  stocks = data.stocks;

  document.getElementById('hdate').textContent = data.date;

  renderPerf(data.hitStats, data.totalAnalyzed);
  renderCards(stocks);
  renderCharts(stocks);
}

init();
