(function(){
  const bar=document.querySelector('.read-progress span');
  const tocLinks=[...document.querySelectorAll('.toc-link')];
  const subtocLinks=[...document.querySelectorAll('.subtoc-link')];
  const sections=tocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const subSections=subtocLinks.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
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
  window.addEventListener('scroll',()=>{updateProgress();updateActive();},{passive:true});
  window.addEventListener('resize',()=>{updateProgress();updateActive();});
  updateProgress(); updateActive();
})();
