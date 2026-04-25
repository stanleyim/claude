// ════════════════════════════════
// 상수
// ════════════════════════════════
const FL = ['수급','모멘텀','거래량','재무','변동성','뉴스','공매도','섹터'];
const FK = ['supply','momentum','volume','fundamental','volatility','news','shortSell','sector'];
const FW = ['25%','20%','15%','13%','10%','8%','5%','4%'];

let stocks=[], mChart=null, radarC=null, barC=null;

// ════════════════════════════════
// 데이터 로드
// ════════════════════════════════
async function loadData(){
  try{
    const r=await fetch('./data/daily_stocks.json?t='+Date.now());
    if(!r.ok) throw new Error('no file');
    const j=await r.json();
    if(j.stocks&&j.stocks.length) return j;
  }catch(e){}
  return null;
}

async function checkMarketStatus(){
  try{
    const r=await fetch('./data/tracking.json?t='+Date.now());
    if(r.ok) return await r.json();
  }catch(e){}
  return null;
}

// ════════════════════════════════
// 휴장일 표시
// ════════════════════════════════
function showHoliday(msg){
  document.getElementById('loading').style.display='none';
  document.getElementById('hdate').textContent=msg;
  document.getElementById('liveBadge').textContent='● 휴장';
  document.getElementById('liveBadge').style.background='rgba(148,163,184,.1)';
  document.getElementById('liveBadge').style.color='#94a3b8';
  document.getElementById('liveBadge').style.borderColor='rgba(148,163,184,.2)';
  document.getElementById('aiText').textContent=msg;
  document.getElementById('aiSub').textContent='다음 거래일 오전 7시에 새로운 TOP 10이 업데이트됩니다.';
  document.getElementById('grid').innerHTML=`
    <div class="holiday-wrap">
      <div class="holiday-icon">🇰🇷</div>
      <div class="holiday-title">${msg}</div>
      <div class="holiday-sub">다음 거래일 오전 7시에 새로운 TOP 10이 업데이트됩니다.</div>
    </div>`;
}

// ════════════════════════════════
// 성과 배너
// ════════════════════════════════
function renderPerf(hitStats, totalAnalyzed){
  const hr=hitStats?.hitRate||0;
  const tp=hitStats?.totalPicks||0;
  const ar=hitStats?.avgReturn||0;
  const el=id=>document.getElementById(id);
  el('hitRate').textContent=tp>0?`${hr}%`:'--';
  el('hitRate').style.color=hr>=60?'var(--green)':hr>=50?'var(--gold)':'var(--text)';
  el('totalPicks').textContent=tp>0?`${tp}건`:'--';
  el('avgReturn').textContent=tp>0?`${ar>=0?'+':''}${ar}%`:'--';
  el('avgReturn').style.color=ar>0?'var(--green)':ar<0?'var(--red)':'var(--text)';
  el('totalAnalyzed').textContent=(totalAnalyzed||0).toLocaleString()+'종목';
}

function renderIdxBar(date, total){
  document.getElementById('idxBar').innerHTML=`
    <div class="idx-card">
      <div class="idx-name">분석일</div>
      <div class="idx-val" style="font-size:.9rem">${date||'-'}</div>
      <div class="idx-chg" style="color:var(--text3)">전일 종가 기준</div>
    </div>
    <div class="idx-card">
      <div class="idx-name">분석 종목 수</div>
      <div class="idx-val">${(total||0).toLocaleString()}</div>
      <div class="idx-chg" style="color:var(--text3)">KOSPI + KOSDAQ</div>
    </div>
    <div class="idx-card">
      <div class="idx-name">9가지 지표</div>
      <div class="idx-val">100점</div>
      <div class="idx-chg up">수급·모멘텀·AI 분석</div>
    </div>`;
}

// ════════════════════════════════
// 종목 카드 렌더링
// ════════════════════════════════
function renderCards(list){
  document.getElementById('grid').innerHTML=list.map((s,i)=>{
    const reasons=s.score?.reasons||[];
    const risk=s.score?.risk||'시장 변동성 유의';
    const bd=s.score?.breakdown||{};
    return `
    <div class="card ${i<3?'r'+(i+1):''}" onclick="openM(${i})">
      <div class="ctop">
        <div class="rank-num">${i+1}</div>
        <div class="name-block">
          <div class="sname">${s.name}</div>
          <div class="smeta">
            <span>${s.code}</span><span>·</span><span>${s.market||''}</span>
            <span class="spill">${s.sector||'기타'}</span>
          </div>
        </div>
        <div class="score-ring">
          <div class="snum">${s.score?.total||0}</div>
          <div class="slbl">AI점수</div>
        </div>
      </div>
      <div class="prow">
        <div class="price">${(s.price||0).toLocaleString()}원</div>
        <div class="chg ${(s.changeRate||0)>=0?'up':'down'}">
          ${(s.changeRate||0)>=0?'+':''}${s.changeRate||0}%
        </div>
      </div>
      <div class="chips">
        ${(s.foreignBuyDays||0)>0?`<span class="chip cf">외인 ${s.foreignBuyDays}일 순매수</span>`:''}
        ${(s.institutionBuyDays||0)>0?`<span class="chip ci">기관 ${s.institutionBuyDays}일 순매수</span>`:''}
        ${(bd.volume||0)>=70?`<span class="chip cv">거래량 급증</span>`:''}
        ${(bd.news||0)>=65?`<span class="chip cn">뉴스 긍정</span>`:''}
      </div>
      ${reasons.length?`
      <div class="reason-box">
        <div class="reason-title">AI 선정 이유</div>
        ${reasons.slice(0,3).map(r=>`<div class="reason-item">${r}</div>`).join('')}
      </div>`:''}
      <div class="risk-box">
        <span style="font-size:.7rem;flex-shrink:0">⚠️</span>
        <span class="risk-text">${risk}</span>
      </div>
      <div class="facs">
        ${FK.map((k,j)=>`
          <div class="fr">
            <div class="fn">${FL[j]}</div>
            <div class="fb"><div class="fbar" style="width:${bd[k]||0}%"></div></div>
            <div class="fv">${bd[k]||0}</div>
          </div>`).join('')}
      </div>
    </div>`;
  }).join('');
}

// ════════════════════════════════
// 차트
// ════════════════════════════════
function renderCharts(list){
  const avg=arr=>arr.reduce((a,b)=>a+b,0)/arr.length;
  if(radarC) radarC.destroy();
  radarC=new Chart(document.getElementById('radar').getContext('2d'),{
    type:'radar',
    data:{labels:FL.map((l,i)=>`${l}(${FW[i]})`),
          datasets:[{label:'평균',data:FK.map(k=>Math.round(avg(list.map(s=>s.score?.breakdown?.[k]||0)))),
            backgroundColor:'rgba(59,130,246,.12)',borderColor:'#3b82f6',
            pointBackgroundColor:'#60a5fa',pointRadius:4,borderWidth:2}]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{r:{min:0,max:100,grid:{color:'rgba(255,255,255,.05)'},
        ticks:{color:'#5a6a88',font:{size:8},stepSize:25,backdropColor:'transparent'},
        pointLabels:{color:'#8899bb',font:{size:9}},
        angleLines:{color:'rgba(255,255,255,.05)'}}},
      plugins:{legend:{display:false}}}
  });

  if(barC) barC.destroy();
  barC=new Chart(document.getElementById('barC').getContext('2d'),{
    type:'bar',
    data:{labels:list.map(s=>s.name),
          datasets:[{label:'AI점수',data:list.map(s=>s.score?.total||0),
            backgroundColor:list.map((_,i)=>i<3?'rgba(245,158,11,.7)':'rgba(59,130,246,.5)'),
            borderColor:list.map((_,i)=>i<3?'#f59e0b':'#3b82f6'),
            borderWidth:1,borderRadius:4}]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{ticks:{color:'#5a6a88',font:{size:8}},grid:{display:false}},
              y:{min:40,max:100,ticks:{color:'#5a6a88',font:{size:8}},
                grid:{color:'rgba(255,255,255,.04)'}}},
      plugins:{legend:{display:false}}}
  });
}

// ════════════════════════════════
// 성과 추적 히스토리
// ════════════════════════════════
function getHistory(){
  try{ return JSON.parse(localStorage.getItem('aiStockHistory')||'[]'); }catch(e){ return []; }
}
function saveHistory(list, date){
  let h=getHistory();
  if(h.find(x=>x.date===date)) return;
  list.forEach(s=>{
    h.push({date,rank:s.rank||0,code:s.code,name:s.name,
      entryPrice:s.price||0,returnRate:0,score:s.score?.total||0,
      reasons:s.score?.reasons||[],risk:s.score?.risk||'',result:'pending'});
  });
  if(h.length>300) h=h.slice(-300);
  localStorage.setItem('aiStockHistory',JSON.stringify(h));
}

function switchTab(t){
  document.querySelectorAll('.ptab').forEach((el,i)=>{
    el.classList.toggle('active',(i===0&&t==='recent')||(i===1&&t==='stats'));
  });
  document.getElementById('tabRecent').style.display=t==='recent'?'':'none';
  document.getElementById('tabStats').style.display=t==='stats'?'':'none';
}

function renderHistory(){
  const h=getHistory().slice(-50).reverse();
  if(!h.length){
    document.getElementById('tabRecent').innerHTML=
      '<p style="font-size:.78rem;color:var(--text3);padding:8px 0">추천 데이터가 쌓이면 자동으로 표시됩니다.</p>';
    return;
  }
  document.getElementById('tabRecent').innerHTML=`
    <table class="htable">
      <thead><tr><th>날짜</th><th>순위</th><th>종목</th><th>추천가</th><th>수익률</th><th>결과</th></tr></thead>
      <tbody>${h.slice(0,30).map(x=>`
        <tr>
          <td style="color:var(--text3)">${x.date}</td>
          <td style="color:var(--text3)">${x.rank||'-'}위</td>
          <td><b>${x.name}</b></td>
          <td>${(x.entryPrice||0).toLocaleString()}</td>
          <td class="${(x.returnRate||0)>=0?'up':'down'}">${(x.returnRate||0)>=0?'+':''}${x.returnRate||0}%</td>
          <td class="${x.result==='hit'?'hit':x.result==='miss'?'miss':'pend'}">
            ${x.result==='hit'?'✅ 적중':x.result==='miss'?'❌ 미적중':'⏳ 대기'}
          </td>
        </tr>`).join('')}
      </tbody>
    </table>`;

  const done=h.filter(x=>x.result!=='pending');
  const hits=done.filter(x=>x.result==='hit');
  const rate=done.length?Math.round(hits.length/done.length*100):0;
  const avgRet=done.length?Math.round(done.reduce((a,x)=>a+(x.returnRate||0),0)/done.length*10)/10:0;
  document.getElementById('tabStats').innerHTML=`
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;padding:4px 0">
      ${[['누적 추천',h.length+'건'],['검증 완료',done.length+'건'],
         ['적중',hits.length+'건'],['적중률',rate+'%'],
         ['평균 수익률',(avgRet>=0?'+':'')+avgRet+'%']].map(([l,v])=>`
        <div style="background:var(--bg3);border-radius:10px;padding:10px 12px">
          <div style="font-size:.65rem;color:var(--text3);margin-bottom:4px">${l}</div>
          <div style="font-family:'Space Grotesk',sans-serif;font-size:1.15rem;font-weight:700">${v}</div>
        </div>`).join('')}
    </div>`;
}

// ════════════════════════════════
// 모달
// ════════════════════════════════
function openM(i){
  const s=stocks[i];
  document.getElementById('mName').textContent=s.name;
  document.getElementById('mMeta').textContent=`${s.code} · ${s.market||''} · ${s.sector||'기타'} · 랭킹 ${s.rank||i+1}위`;
  document.getElementById('mStats').innerHTML=[
    ['현재가',(s.price||0).toLocaleString()+'원',''],
    ['등락률',(s.changeRate>=0?'+':'')+s.changeRate+'%',s.changeRate>=0?'up':'down'],
    ['AI점수',(s.score?.total||0)+'점','accent2'],
    ['PER/ROE',(s.per||'-')+'/'+(s.roe||'-')+'%',''],
  ].map(([l,v,cls])=>`<div class="mst"><div class="mstl">${l}</div>
    <div class="mstv" ${cls==='up'?'style="color:var(--green)"':cls==='down'?'style="color:var(--red)"':cls==='accent2'?'style="color:var(--accent2)"':''}>${v}</div></div>`).join('');

  if(mChart) mChart.destroy();
  const c=s.closes||[];
  mChart=new Chart(document.getElementById('mChart').getContext('2d'),{
    type:'line',
    data:{labels:Array.from({length:c.length},(_,i)=>i+1),
          datasets:[{data:c,borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,.07)',
            borderWidth:1.5,pointRadius:0,fill:true,tension:.3}]},
    options:{responsive:true,maintainAspectRatio:false,
      scales:{x:{display:false},y:{grid:{color:'rgba(255,255,255,.04)'},
        ticks:{color:'#5a6a88',font:{size:8},callback:v=>v>=1000?(v/1000).toFixed(0)+'K':v}}},
      plugins:{legend:{display:false}}}
  });

  const reasons=s.score?.reasons||[];
  document.getElementById('mReasons').innerHTML=
    reasons.length?reasons.map(r=>`<div class="mritem">${r}</div>`).join('')
    :'<div style="font-size:.75rem;color:var(--text3)">분석 데이터 없음</div>';
  document.getElementById('mRisk').textContent=s.score?.risk||'시장 변동성 유의';
  document.getElementById('mFactors').innerHTML=FK.map((k,j)=>`
    <div class="mfrow">
      <div class="mfn">${FL[j]}</div>
      <div class="mfb"><div class="mfbar" style="width:${s.score?.breakdown?.[k]||0}%"></div></div>
      <div class="mfp">${s.score?.breakdown?.[k]||0}점</div>
      <div class="mfw">${FW[j]}</div>
    </div>`).join('');

  document.getElementById('moverlay').classList.add('open');
}

function closeM(e){
  if(!e||e.target===document.getElementById('moverlay'))
    document.getElementById('moverlay').classList.remove('open');
}

// ════════════════════════════════
// AI 코멘트
// ════════════════════════════════
async function getAIComment(s){
  if(s.score?.reasons?.length) return null;
  const p=`당신은 대한민국 최고의 주식 분석가입니다.
다음 종목 데이터를 분석해 JSON으로만 응답하세요.
{"reason":["이유1","이유2","이유3"],"risk":"리스크 1문장"}

종목: ${s.name}(${s.sector||''}) | 현재가: ${(s.price||0).toLocaleString()}원 | 등락: ${s.changeRate>=0?'+':''}${s.changeRate}%
AI점수: ${s.score?.total||0}점 | 수급:${s.score?.breakdown?.supply||0} 모멘텀:${s.score?.breakdown?.momentum||0}`;
  try{
    const r=await fetch('https://api.anthropic.com/v1/messages',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({model:'claude-sonnet-4-20250514',max_tokens:1000,
        messages:[{role:'user',content:p}]})
    });
    const d=await r.json();
    const txt=d.content?.[0]?.text?.trim()||'';
    return JSON.parse(txt.replace(/```json|```/g,'').trim());
  }catch(e){ return null; }
}

// ════════════════════════════════
// 메인 초기화
// ════════════════════════════════
async function init(){
  // 주말 즉시 체크
  const day=new Date().getDay();
  if(day===0||day===6){
    showHoliday('주말 — 증시 휴장일입니다 🇰🇷');
    return;
  }

  const data=await loadData();
  document.getElementById('loading').style.display='none';

  // 휴장일 체크
  if(data?.isHoliday){
    showHoliday(data.message||'오늘은 증시 휴장일입니다 🇰🇷');
    return;
  }
  if(!data){
    const status=await checkMarketStatus();
    if(status?.isHoliday){
      showHoliday(status.message||'오늘은 증시 휴장일입니다 🇰🇷');
      return;
    }
    document.getElementById('aiText').textContent=
      'GitHub Actions에서 아직 데이터가 생성되지 않았습니다. Actions → "Run workflow"를 실행해주세요.';
    document.getElementById('hdate').textContent='데이터 대기 중';
    document.getElementById('liveBadge').textContent='● 대기';
    document.getElementById('liveBadge').style.color='var(--gold)';
    renderHistory();
    return;
  }

  stocks=data.stocks||[];
  const hitStats=data.hitStats||{};

  document.getElementById('hdate').textContent=`${data.date} 전일 종가 기준`;
  document.getElementById('aiSub').textContent=
    `📅 ${data.date} | ${(data.totalAnalyzed||0).toLocaleString()}개 종목 분석 완료`;

  renderPerf(hitStats, data.totalAnalyzed);
  renderIdxBar(data.date, data.totalAnalyzed);
  saveHistory(stocks, data.date);
  renderCards(stocks);
  renderCharts(stocks);
  renderHistory();

  // AI 코멘트 보완
  for(let i=0;i<stocks.length;i++){
    if(!stocks[i].score?.reasons?.length){
      const ai=await getAIComment(stocks[i]);
      if(ai){
        stocks[i].score.reasons=ai.reason||[];
        stocks[i].score.risk=ai.risk||stocks[i].score.risk;
        renderCards(stocks);
      }
    }
  }

  // AI 시장 요약
  const top3=stocks.slice(0,3).map(s=>s.name).join(', ');
  try{
    const r=await fetch('https://api.anthropic.com/v1/messages',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({model:'claude-sonnet-4-20250514',max_tokens:1000,
        messages:[{role:'user',content:
          `오늘 ${(data.totalAnalyzed||0).toLocaleString()}개 종목 분석 결과 ${top3} 등이 상위권에 선정됐습니다. 한국 개인 투자자에게 오늘의 핵심 투자 포인트를 2문장으로 알려주세요.`}]})
    });
    const d=await r.json();
    document.getElementById('aiText').textContent=
      d.content?.[0]?.text?.trim()||`오늘 ${top3} 등이 AI 분석 상위권에 선정됐습니다.`;
  }catch(e){
    document.getElementById('aiText').textContent=
      `오늘 ${top3} 등이 9개 팩터 AI 분석에서 상위권에 선정됐습니다.`;
  }
}

init();
