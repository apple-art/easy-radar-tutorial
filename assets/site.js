(function(){
  const bar=document.querySelector('.read-progress span');
  const links=[...document.querySelectorAll('.toc-link')];
  const sections=links.map(a=>document.querySelector(a.getAttribute('href'))).filter(Boolean);
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
    links.forEach(a=>a.classList.toggle('active', current && a.getAttribute('href')==='#'+current.id));
  }
  window.addEventListener('scroll',()=>{updateProgress();updateActive();},{passive:true});
  window.addEventListener('resize',()=>{updateProgress();updateActive();});
  updateProgress(); updateActive();
})();
