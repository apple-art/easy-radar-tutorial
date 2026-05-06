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
