// 페이지 로드되면 자동 실행
window.onload = function () {
  loadStocks();
};

async function loadStocks() {
  try {
    // GitHub Pages 기준 (중요!)
    const res = await fetch('./data/daily_stocks.json');

    if (!res.ok) {
      throw new Error('데이터 불러오기 실패');
    }

    const data = await res.json();

    console.log('불러온 데이터:', data);

    const container = document.getElementById('stock-list');

    if (!container) {
      console.error('stock-list div 없음');
      return;
    }

    container.innerHTML = '';

    // 👉 무료/유료 구조 (일단 무료 5개만 표시)
    const stocksToShow = data.stocks.slice(0, 5);

    stocksToShow.forEach(stock => {
      const div = document.createElement('div');

      div.style.border = '1px solid #ddd';
      div.style.padding = '10px';
      div.style.marginBottom = '10px';
      div.style.borderRadius = '8px';

      div.innerHTML = `
        <h3>${stock.name} (${stock.code})</h3>
        <p>가격: ${stock.price.toLocaleString()}원</p>
        <p>등락률: ${stock.changeRate}%</p>
        <p>PER: ${stock.per} | ROE: ${stock.roe}</p>
      `;

      container.appendChild(div);
    });

  } catch (error) {
    console.error('에러 발생:', error);

    const container = document.getElementById('stock-list');
    if (container) {
      container.innerHTML = '<p>데이터를 불러오지 못했습니다.</p>';
    }
  }
}
