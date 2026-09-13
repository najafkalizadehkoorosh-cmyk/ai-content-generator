(() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const progress = document.getElementById('progress');
  const art = document.getElementById('heroArt');
  const cards = [...document.querySelectorAll('.product-card')];
  const steps = [...document.querySelectorAll('.journey-step')];
  const line = document.getElementById('journeyLine');

  function clamp(v,min,max){return Math.max(min,Math.min(max,v));}
  function update(){
    const y=window.scrollY;
    const max=document.documentElement.scrollHeight-window.innerHeight;
    progress.style.width=(max>0?(y/max)*100:0)+'%';
    if(!reduce){
      const heroEnd=Math.max(1,window.innerHeight*.9);
      const p=clamp(y/heroEnd,0,1);
      art.style.transform=`translateY(${p*70}px) rotate(${2-p*7}deg) scale(${1-p*.05})`;
      art.style.borderRadius=`${50-p*20}% ${50+p*15}% ${12+p*25}% ${12+p*25}%`;
      cards.forEach((card,i)=>{
        const r=card.getBoundingClientRect();
        const center=window.innerHeight*.62;
        const delta=(r.top+ r.height/2-center)/window.innerHeight;
        const amount=parseFloat(card.dataset.speed)||0;
        card.style.transform=`translateY(${clamp(delta*amount,-34,34)}px) rotate(${clamp(-delta*(i%2?1.5:-1.2),-2,2)}deg)`;
      });
      const jt=document.querySelector('.journey-track')?.getBoundingClientRect();
      if(jt){
        const local=clamp((window.innerHeight*.72-jt.top)/(jt.height*.82),0,1);
        line.style.height=(local*100)+'%';
        steps.forEach((s,i)=>{
          const r=s.getBoundingClientRect();
          const active=r.top<window.innerHeight*.72&&r.bottom>window.innerHeight*.18;
          s.style.opacity=active?1:.34;
          s.style.transform=active?'translateX(0)':`translateX(${r.top>window.innerHeight*.72?25:-18}px)`;
        });
      }
    }
  }
  let ticking=false;
  window.addEventListener('scroll',()=>{if(!ticking){requestAnimationFrame(()=>{update();ticking=false});ticking=true}},{passive:true});
  window.addEventListener('resize',update,{passive:true});
  update();
})();
