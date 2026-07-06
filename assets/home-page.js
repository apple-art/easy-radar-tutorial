(function(){
  const bar = document.querySelector('.read-progress span');

  function updateProgress(){
    if(!bar) return;
    const max = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = (max > 0 ? window.scrollY / max * 100 : 0).toFixed(2) + '%';
  }

  window.addEventListener('scroll', updateProgress, { passive: true });
  window.addEventListener('resize', updateProgress);
  updateProgress();
})();

// Site black/white theme toggle
(function(){
  const toggles = [...document.querySelectorAll('[data-theme-toggle]')];
  if(!toggles.length) return;

  const key = 'easy-radar-theme';
  const legacyKey = 'easy-radar-home-theme';
  const root = document.documentElement;
  const isZh = document.documentElement.lang.toLowerCase().startsWith('zh');

  function normalizeTheme(value){
    return value === 'dark' ? 'dark' : 'light';
  }

  function setTheme(theme){
    const next = normalizeTheme(theme);
    if(next === 'dark'){
      root.setAttribute('data-theme', 'dark');
      root.setAttribute('data-home-theme', 'dark');
    }else{
      root.removeAttribute('data-theme');
      root.removeAttribute('data-home-theme');
    }
    try{
      localStorage.setItem(key, next);
      localStorage.setItem(legacyKey, next);
    }catch(_){}
    toggles.forEach(button => {
      const dark = next === 'dark';
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', isZh ? (dark ? '切换到白色背景' : '切换到黑色背景') : (dark ? 'Switch to white background' : 'Switch to black background'));
      button.setAttribute('title', isZh ? (dark ? '白色背景' : '黑色背景') : (dark ? 'White background' : 'Black background'));
    });
  }

  let saved = 'light';
  try{
    saved = localStorage.getItem(key) || localStorage.getItem(legacyKey) || (root.getAttribute('data-theme') === 'dark' || root.getAttribute('data-home-theme') === 'dark' ? 'dark' : 'light');
  }catch(_){}
  setTheme(saved);

  toggles.forEach(button => {
    button.addEventListener('click', () => {
      setTheme(root.getAttribute('data-theme') === 'dark' || root.getAttribute('data-home-theme') === 'dark' ? 'light' : 'dark');
    });
  });
})();

// Appreciation modal
(function(){
  const btn = document.getElementById('appreciationBtn');
  const modal = document.getElementById('appreciationModal');
  const closeBtn = document.getElementById('modalClose');
  const overlay = modal?.querySelector('.modal-overlay');

  if(!btn || !modal) return;

  function openModal(){
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal(){
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', openModal);
  closeBtn?.addEventListener('click', closeModal);
  overlay?.addEventListener('click', closeModal);

  document.addEventListener('keydown', event => {
    if(event.key === 'Escape' && modal.getAttribute('aria-hidden') === 'false'){
      closeModal();
    }
  });
})();

// ECharts cognitive curve initialization
(function(){
  const chartDom = document.getElementById('curve-chart');
  if(!chartDom) return;

  const echartsSrc = 'https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js';
  let chart = null;
  let loading = false;

  function renderFallbackChart(){
    const isZh = document.documentElement.lang.toLowerCase().startsWith('zh');
    chartDom.innerHTML = `
      <svg class="curve-fallback" viewBox="0 0 720 360" role="img" aria-label="${isZh ? '认知曲线对比图' : 'Learning curve comparison'}">
        <defs>
          <linearGradient id="easyCurveFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="rgba(135, 182, 162, 0.34)"/>
            <stop offset="1" stop-color="rgba(135, 182, 162, 0.04)"/>
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="720" height="360" rx="18" fill="#fffdf7"/>
        <g stroke="#e8e2d8" stroke-dasharray="7 9" stroke-width="1">
          <path d="M92 80H648"/><path d="M92 132H648"/><path d="M92 184H648"/><path d="M92 236H648"/><path d="M92 288H648"/>
        </g>
        <g fill="#4a5751" font-family="Inter, system-ui, sans-serif" font-size="15" font-weight="700">
          <text x="104" y="320">${isZh ? '第1章' : 'Ch. 1'}</text><text x="230" y="320">${isZh ? '第2章' : 'Ch. 2'}</text><text x="356" y="320">${isZh ? '第3章' : 'Ch. 3'}</text><text x="482" y="320">${isZh ? '第4章' : 'Ch. 4'}</text><text x="608" y="320">${isZh ? '第5章' : 'Ch. 5'}</text>
          <text x="34" y="62" transform="rotate(-90 34 62)">${isZh ? '认知难度' : 'Difficulty'}</text>
        </g>
        <path d="M118 285 C190 270 218 250 244 230 C292 196 318 177 370 150 C448 112 506 95 622 82 L622 288 L118 288Z" fill="url(#easyCurveFill)"/>
        <path d="M118 285 C190 270 218 250 244 230 C292 196 318 177 370 150 C448 112 506 95 622 82" fill="none" stroke="#87b6a2" stroke-width="5" stroke-linecap="round"/>
        <path d="M118 285 C206 275 238 262 272 242 C334 205 342 88 402 82 C482 74 548 76 622 72" fill="none" stroke="#d97757" stroke-width="5" stroke-linecap="round"/>
        <g fill="#87b6a2" stroke="#fff" stroke-width="4">
          <circle cx="118" cy="285" r="8"/><circle cx="244" cy="230" r="8"/><circle cx="370" cy="150" r="8"/><circle cx="496" cy="98" r="8"/><circle cx="622" cy="82" r="8"/>
        </g>
        <g fill="#d97757" stroke="#fff" stroke-width="4">
          <circle cx="118" cy="285" r="8"/><circle cx="244" cy="242" r="8"/><circle cx="370" cy="82" r="8"/><circle cx="496" cy="78" r="8"/><circle cx="622" cy="72" r="8"/>
        </g>
        <g font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="800">
          <circle cx="474" cy="40" r="6" fill="#87b6a2"/><text x="490" y="45" fill="#4a5751">${isZh ? '本教程' : 'This tutorial'}</text>
          <circle cx="578" cy="40" r="6" fill="#d97757"/><text x="594" y="45" fill="#4a5751">${isZh ? '传统教材' : 'Traditional'}</text>
        </g>
      </svg>
    `;
  }

  function initChart(){
    if(chart || typeof echarts === 'undefined') return;

    chart = echarts.init(chartDom);
    chart.setOption({
      legend: {
        data: ['本教程', '传统教材'],
        top: '8%',
        right: '10%',
        textStyle: { color: '#4a5751', fontSize: 13, fontWeight: 600 }
      },
      grid: { left: '12%', right: '8%', top: '22%', bottom: '15%' },
      xAxis: {
        type: 'category',
        data: ['第1章', '第2章', '第3章', '第4章', '第5章'],
        axisLine: { lineStyle: { color: '#7d8b84' } },
        axisLabel: { color: '#4a5751', fontSize: 13, fontWeight: 600 }
      },
      yAxis: {
        type: 'value',
        name: '认知难度',
        nameTextStyle: { color: '#4a5751', fontSize: 13, fontWeight: 600 },
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        splitLine: { lineStyle: { color: '#e5e5e5', type: 'dashed' } }
      },
      series: [
        {
          name: '本教程',
          data: [1, 1.8, 3.2, 4.8, 6.5],
          type: 'line',
          smooth: true,
          lineStyle: { color: '#87b6a2', width: 3 },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(135, 182, 162, 0.3)' },
                { offset: 1, color: 'rgba(135, 182, 162, 0.05)' }
              ]
            }
          },
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: { color: '#87b6a2', borderColor: '#fff', borderWidth: 2 }
        },
        {
          name: '传统教材',
          data: [1, 1.5, 6.8, 7.2, 7.5],
          type: 'line',
          smooth: true,
          lineStyle: { color: '#d97757', width: 3 },
          symbol: 'circle',
          symbolSize: 8,
          itemStyle: { color: '#d97757', borderColor: '#fff', borderWidth: 2 }
        }
      ]
    });
    window.addEventListener('resize', () => chart.resize());
  }

  function loadEcharts(){
    if(typeof echarts !== 'undefined'){
      initChart();
      return;
    }
    if(loading) return;
    loading = true;
    const script = document.createElement('script');
    script.src = echartsSrc;
    script.defer = true;
    script.onload = initChart;
    document.head.appendChild(script);
  }

  renderFallbackChart();

  if('IntersectionObserver' in window){
    const observer = new IntersectionObserver(entries => {
      if(entries.some(entry => entry.isIntersecting)){
        observer.disconnect();
        loadEcharts();
      }
    }, { rootMargin: '360px 0px' });
    observer.observe(chartDom);
  }else{
    window.addEventListener('load', loadEcharts, { once: true });
  }
})();
