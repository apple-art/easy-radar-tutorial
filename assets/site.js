(function(){
  const bar=document.querySelector('.read-progress span');
  const tocLinks=[...document.querySelectorAll('.toc-link')];
  const subtocLinks=[...document.querySelectorAll('.subtoc-link')];
  const sections=tocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const subSections=subtocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const articleLayout=document.querySelector('.article-layout');
  const sidebar=document.querySelector('.sidebar');
  const storageKey='easy-radar-toc-collapsed';
  let tocToggle=null;
  function setTocCollapsed(collapsed){
    document.body.classList.toggle('toc-collapsed', collapsed);
    if(tocToggle){
      tocToggle.setAttribute('aria-expanded', String(!collapsed));
      const icon=collapsed
        ? '<svg viewBox="0 0 28 28" aria-hidden="true"><path class="toc-toggle-rail" d="M22 6.5v15"/><path d="m9.5 7.5 6.5 6.5-6.5 6.5"/><path d="m14.5 7.5 6.5 6.5-6.5 6.5"/></svg>'
        : '<svg viewBox="0 0 28 28" aria-hidden="true"><path class="toc-toggle-rail" d="M6 6.5v15"/><path d="m18.5 7.5-6.5 6.5 6.5 6.5"/><path d="m13.5 7.5-6.5 6.5 6.5 6.5"/></svg>';
      tocToggle.innerHTML=icon;
      tocToggle.setAttribute('aria-label', collapsed ? '展开目录' : '收起目录');
      tocToggle.setAttribute('title', collapsed ? '展开目录' : '收起目录');
    }
    try{ localStorage.setItem(storageKey, collapsed ? '1' : '0'); }catch(_){}
  }
  if(articleLayout && sidebar){
    tocToggle=document.createElement('button');
    tocToggle.type='button';
    tocToggle.className='toc-toggle';
    tocToggle.setAttribute('aria-controls','book-toc-sidebar');
    sidebar.id=sidebar.id || 'book-toc-sidebar';
    sidebar.appendChild(tocToggle);
    let saved=false;
    try{ saved=localStorage.getItem(storageKey)==='1'; }catch(_){}
    setTocCollapsed(saved);
    tocToggle.addEventListener('click',()=>setTocCollapsed(!document.body.classList.contains('toc-collapsed')));
  }
  function escapeCode(text){
    return text.replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  }
  function highlightMatlabLine(line){
    const keywords=new Set(['break','case','catch','classdef','continue','else','elseif','end','for','function','global','if','otherwise','parfor','persistent','return','spmd','switch','try','while']);
    const builtins=new Set(['abs','angle','axis','ceil','close','clc','clear','colorbar','conj','conv','cos','db','disp','exp','fft','fftshift','figure','find','floor','fliplr','grid','ifft','imag','imagesc','length','linspace','log10','max','mean','min','ones','plot','randn','real','round','sin','size','sqrt','strel','sum','title','xlabel','ylabel','zeros']);
    let html='';
    let index=0;
    while(index<line.length){
      const rest=line.slice(index);
      const char=line[index];
      if(char==='%'){
        html+=`<span class="code-comment">${escapeCode(rest)}</span>`;
        break;
      }
      if(char==="'"){
        let end=index+1;
        while(end<line.length){
          if(line[end]==="'"){
            end+=1;
            if(line[end]==="'"){
              end+=1;
              continue;
            }
            break;
          }
          end+=1;
        }
        html+=`<span class="code-string">${escapeCode(line.slice(index,end))}</span>`;
        index=end;
        continue;
      }
      const number=rest.match(/^\d+(?:\.\d+)?(?:e[+-]?\d+)?/i);
      if(number){
        html+=`<span class="code-number">${number[0]}</span>`;
        index+=number[0].length;
        continue;
      }
      const word=rest.match(/^[A-Za-z_]\w*/);
      if(word){
        const token=word[0];
        const className=keywords.has(token) ? 'code-keyword' : builtins.has(token) ? 'code-function' : '';
        html+=className ? `<span class="${className}">${token}</span>` : escapeCode(token);
        index+=token.length;
        continue;
      }
      if(/[()[\]{}.,;:+\-*\/\\=<>~&|^]/.test(char)){
        html+=`<span class="code-operator">${escapeCode(char)}</span>`;
      }else{
        html+=escapeCode(char);
      }
      index+=1;
    }
    return html;
  }
  document.querySelectorAll('pre code.language-matlab').forEach(code=>{
    code.innerHTML=code.textContent.split('\n').map(highlightMatlabLine).join('\n');
    code.classList.add('is-highlighted');
  });
  function updateProgress(){
    if(!bar)return;
    const max=document.documentElement.scrollHeight-window.innerHeight;
    bar.style.width=(max>0?window.scrollY/max*100:0).toFixed(2)+'%';
  }
  function updateActive(){
    let current=sections[0];
    for(const sec of sections){
      if(sec.getBoundingClientRect().top<160) current=sec;
    }
    let currentSub=null;
    const currentSection=current && current.closest ? current.closest('.chapter-section') : null;
    for(const sec of subSections){
      if(sec.closest('.chapter-section')===currentSection && sec.getBoundingClientRect().top<260) currentSub=sec;
    }
    tocLinks.forEach(a=>a.classList.toggle('active', current && a.getAttribute('href')==='#'+current.id));
    subtocLinks.forEach(a=>a.classList.toggle('active', currentSub && a.getAttribute('href')==='#'+currentSub.id));
    document.querySelectorAll('.toc-section').forEach(group=>{
      group.classList.toggle('open', current && group.dataset.section===current.id);
    });
  }
  function scrollToHash(hash){
    if(!hash || hash==='#')return false;
    const target=document.getElementById(decodeURIComponent(hash.slice(1)));
    if(!target)return false;
    const offset=document.querySelector('.article-top')?96:0;
    const top=target.getBoundingClientRect().top+window.scrollY-offset;
    window.scrollTo({top:Math.max(0,top),behavior:'smooth'});
    return true;
  }
  document.addEventListener('click',event=>{
    const link=event.target.closest('.toc-link,.subtoc-link');
    if(!link || !link.hash || link.pathname!==window.location.pathname)return;
    if(!scrollToHash(link.hash))return;
    event.preventDefault();
    history.pushState(null,'',link.hash);
    updateActive();
    window.setTimeout(updateActive,350);
    window.setTimeout(updateActive,900);
  });
  window.addEventListener('scroll',()=>{updateProgress();updateActive();},{passive:true});
  window.addEventListener('resize',()=>{updateProgress();updateActive();});
  window.addEventListener('load',()=>{
    if(location.hash)scrollToHash(location.hash);
    window.setTimeout(updateActive,350);
  });
  updateProgress(); updateActive();
})();

// Site black/white theme toggle
(function(){
  const toggles=[...document.querySelectorAll('[data-theme-toggle]')];
  if(!toggles.length) return;

  const key='easy-radar-theme';
  const legacyKey='easy-radar-home-theme';
  const root=document.documentElement;
  const isZh=document.documentElement.lang.toLowerCase().startsWith('zh');

  function normalizeTheme(value){
    return value==='dark' ? 'dark' : 'light';
  }

  function setTheme(theme){
    const next=normalizeTheme(theme);
    if(next==='dark'){
      root.setAttribute('data-theme','dark');
      root.setAttribute('data-home-theme','dark');
    }else{
      root.removeAttribute('data-theme');
      root.removeAttribute('data-home-theme');
    }
    try{
      localStorage.setItem(key,next);
      localStorage.setItem(legacyKey,next);
    }catch(_){}
    toggles.forEach(button=>{
      const dark=next==='dark';
      button.setAttribute('aria-pressed',String(dark));
      button.setAttribute('aria-label',isZh ? (dark ? '切换到白色背景' : '切换到黑色背景') : (dark ? 'Switch to white background' : 'Switch to black background'));
      button.setAttribute('title',isZh ? (dark ? '白色背景' : '黑色背景') : (dark ? 'White background' : 'Black background'));
    });
  }

  let saved='light';
  try{ saved=localStorage.getItem(key) || localStorage.getItem(legacyKey) || (root.getAttribute('data-theme')==='dark' || root.getAttribute('data-home-theme')==='dark' ? 'dark' : 'light'); }catch(_){}
  setTheme(saved);

  toggles.forEach(button=>{
    button.addEventListener('click',()=>{
      setTheme(root.getAttribute('data-theme')==='dark' || root.getAttribute('data-home-theme')==='dark' ? 'light' : 'dark');
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

  function openModal() {
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  btn.addEventListener('click', openModal);
  closeBtn?.addEventListener('click', closeModal);
  overlay?.addEventListener('click', closeModal);

  document.addEventListener('keydown', (e) => {
    if(e.key === 'Escape' && modal.getAttribute('aria-hidden') === 'false') {
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

  function initChart() {
    if(chart || typeof echarts === 'undefined') return;

    chart = echarts.init(chartDom);
    const option = {
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
    };

    chart.setOption(option);
    window.addEventListener('resize', () => chart.resize());
  }

  function loadEcharts() {
    if(typeof echarts !== 'undefined') {
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

  if('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      if(entries.some(entry => entry.isIntersecting)) {
        observer.disconnect();
        loadEcharts();
      }
    }, { rootMargin: '360px 0px' });
    observer.observe(chartDom);
  } else {
    window.addEventListener('load', loadEcharts, { once: true });
  }
})();
