const $=s=>document.querySelector(s);
const state={plan:null};

const rules=[
  {keys:["پژوهش","تحقیق","مقاله","علمی","منبع","research"],add:["research","evidence","writing","factcheck"]},
  {keys:["سایت","وب","فروشگاه","website","frontend","صفحه","واکنش‌گرا"],add:["architecture","ui","frontend","seo","security","testing"]},
  {keys:["کد","برنامه","پایتون","اپ","اتوماسیون","csv","excel"],add:["architecture","coding","testing","security"]},
  {keys:["عکس","تصویر","پوستر","visual","image"],add:["visual"]},
  {keys:["امنیت","رمز","login","احراز"],add:["security"]},
  {keys:["تست","testing","bug","خطا"],add:["testing"]}
];

const catalog={
 architecture:{name:"معماری و طراحی راه‌حل",kind:"Planning",desc:"تبدیل هدف به ساختار، اجزای اصلی و وابستگی‌ها.",base:3},
 research:{name:"تحقیق و جمع‌آوری منابع",kind:"Research",desc:"پیدا کردن اطلاعات و منابع مرتبط؛ بدون ساخت ادعای بی‌منبع.",base:4},
 evidence:{name:"استخراج شواهد",kind:"Analysis",desc:"تبدیل منابع به یافته‌ها، اعداد و نکات قابل استناد.",base:4},
 writing:{name:"نگارش خروجی",kind:"Writing",desc:"تبدیل شواهد و طرح به متن نهایی با ساختار مشخص.",base:3},
 factcheck:{name:"راستی‌آزمایی",kind:"Quality",desc:"بررسی ادعاها، تناقض‌ها و پیوند ادعا به منبع.",base:4},
 ui:{name:"طراحی رابط کاربری",kind:"Design",desc:"تعیین ساختار صفحات، اجزا، حالات و رفتار واکنش‌گرا.",base:3},
 frontend:{name:"پیاده‌سازی Frontend",kind:"Build",desc:"تبدیل طرح به کد قابل اجرا و responsive.",base:4},
 seo:{name:"SEO",kind:"Quality",desc:"ساختار معنایی، metadata و دسترسی‌پذیری.",base:3},
 security:{name:"بررسی امنیت",kind:"Security",desc:"جست‌وجوی الگوهای پرخطر و ارائه اصلاح مشخص.",base:4},
 testing:{name:"تست و کنترل کیفیت",kind:"QA",desc:"تعریف و اجرای آزمون‌های لازم و کنترل خطاهای اصلی.",base:3},
 coding:{name:"تولید کد",kind:"Build",desc:"پیاده‌سازی task در فناوری مناسب پروژه.",base:4},
 visual:{name:"تولید یا طراحی تصویر",kind:"Visual",desc:"تعریف تصویر موردنیاز و انتخاب مسیر تولید مناسب.",base:3}
};

function esc(v){return String(v).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;"}[c]));}
function clamp(n,a,b){return Math.max(a,Math.min(b,n));}
function difficulty(text,base){
 let d=base;
 if(text.length>220)d++;
 if(/پیچیده|حرفه‌ای|تخصصی|کامل|enterprise|production/i.test(text))d++;
 if(/ساده|سریع|مختصر/i.test(text))d--;
 return clamp(d,1,5);
}
function estimateTokens(text){return Math.max(40,Math.ceil(text.length/4));}
function detectTypes(text){
 const found=new Set(["architecture"]);
 const lower=text.toLowerCase();
 rules.forEach(r=>{if(r.keys.some(k=>text.includes(k)||lower.includes(k.toLowerCase())))r.add.forEach(x=>found.add(x));});
 if(found.has("research"))found.add("factcheck");
 if(found.has("frontend"))found.add("testing");
 return Array.from(found);
}
function providerFor(d,kind){
 if(kind==="Visual")return "Free image-capable provider / local workflow";
 if(d>=4)return "Strongest available free/local model";
 if(d>=3)return "Balanced free/local model";
 return "Fast free/local model";
}
function buildPlan(){
 const req=$("#requestInput").value.trim();
 $("#validation").textContent="";
 if(req.length<12){$("#validation").textContent="درخواست خیلی کوتاه است؛ یک جمله کامل‌تر بنویس.";return;}
 const types=detectTypes(req);
 const tasks=types.map((type,i)=>{
  const c=catalog[type]||catalog.architecture;
  const diff=difficulty(req,c.base);
  const inputTokens=estimateTokens(req)+160+(diff*35);
  const outputTokens=220+(diff*120);
  return {id:i+1,type:type,name:c.name,kind:c.kind,desc:c.desc,diff:diff,inputTokens:inputTokens,outputTokens:outputTokens,total:inputTokens+outputTokens,provider:providerFor(diff,c.kind)};
 });
 const mode=$("#tokenMode").value;
 const mult=mode==="aggressive"?.62:mode==="balanced"?.78:1;
 state.plan={title:req.length>70?req.slice(0,67)+"…":req,goal:req,quality:$("#quality").value,tokenMode:mode,budget:"0 تومان",tasks:tasks,total:Math.ceil(tasks.reduce((s,t)=>s+t.total,0)*mult)};
 $("#emptyState").classList.add("hidden");
 $("#planView").classList.remove("hidden");
 $("#approvalBar").classList.remove("hidden");
 $("#planStatus").textContent="Preview آماده است";
 renderPlan();
}
function renderPlan(){
 const p=state.plan;
 let html='<div class="plan-wrap"><div class="hero-card"><div class="hero-title">'+esc(p.title)+'</div><div class="meta-grid">';
 html+='<div class="meta"><small>کیفیت</small><strong>'+esc(p.quality)+'</strong></div>';
 html+='<div class="meta"><small>بودجه</small><strong>'+esc(p.budget)+'</strong></div>';
 html+='<div class="meta"><small>Token تخمینی</small><strong>'+p.total.toLocaleString("en-US")+'</strong></div>';
 html+='<div class="meta"><small>تعداد Task</small><strong>'+p.tasks.length+'</strong></div></div></div>';
 html+='<div class="section-title">جزئیات برنامه</div>';
 p.tasks.forEach(t=>{
  html+='<div class="task-card"><div class="task-top"><div class="task-name">'+t.id+'. '+esc(t.name)+'</div><span class="tag">'+esc(t.kind)+'</span></div>';
  html+='<p style="color:var(--muted);font-size:12px;line-height:1.8">'+esc(t.desc)+'</p>';
  html+='<div class="task-grid"><div>سختی<strong>'+t.diff+'/5</strong></div><div>Provider<strong>'+esc(t.provider)+'</strong></div><div>Input<strong>'+t.inputTokens.toLocaleString("en-US")+'</strong></div><div>Output<strong>'+t.outputTokens.toLocaleString("en-US")+'</strong></div></div></div>';
 });
 html+='<div class="section-title">قوانین اجرا</div><div class="task-card"><p style="margin:0;color:var(--muted);font-size:12px;line-height:1.9">فقط Taskهای لازم اجرا می‌شوند؛ Context به بخش مرتبط محدود می‌شود؛ نتایج قابل cache خلاصه می‌شوند؛ و عملیات ساخت یا تغییر مهم فقط پس از تأیید تو انجام می‌شود.</p></div></div>';
 $("#planView").innerHTML=html;
}
function execute(){
 if(!state.plan)return;
 $("#approvalBar").classList.add("hidden");
 $("#executionPanel").classList.remove("hidden");
 $("#executionStatus").textContent="در حال اجرای شبیه‌ساز";
 const list=$("#taskList");
 list.innerHTML="";
 state.plan.tasks.forEach(t=>{
  const card=document.createElement("div");card.className="run-card";card.id="run-"+t.id;
  card.innerHTML='<div class="run-head"><strong>'+esc(t.name)+'</strong><span class="state running">در صف اجرا</span></div><p style="color:var(--muted);font-size:12px;margin:8px 0 0">'+esc(t.provider)+'</p>';
  list.appendChild(card);
 });
 let i=0;
 const step=()=>{
  if(i>=state.plan.tasks.length){
   $("#executionStatus").textContent="پایان اجرای MVP";
   $("#finalBox").innerHTML="<strong>Preview اجرا شد.</strong><p style='margin:7px 0 0;color:var(--muted);font-size:12px'>در نسخه بعدی همین موتور به Providerهای واقعی، حافظه پروژه، cache و ابزارهای تحقیق و کدنویسی متصل می‌شود. این MVP عمداً هیچ API پولی را خودکار صدا نمی‌زند.</p>";
   return;
  }
  const card=$("#run-"+state.plan.tasks[i].id);
  const st=card.querySelector(".state");st.textContent="انجام شد";st.className="state done";i++;setTimeout(step,280);
 };
 step();
}
$("#planBtn").addEventListener("click",buildPlan);
$("#approveBtn").addEventListener("click",execute);
$("#editBtn").addEventListener("click",()=>{$("#requestInput").focus();$("#approvalBar").classList.add("hidden");$("#planStatus").textContent="در حال ویرایش";});
$("#exampleBtn").addEventListener("click",()=>{$("#requestInput").value="یک پژوهش علمی درباره تأثیر خواب بر حافظه دانش‌آموزان تهیه کن؛ منابع معتبر، ساختار مقاله و پیشنهاد تصویر می‌خواهم.";});
document.querySelectorAll("[data-example]").forEach(b=>b.addEventListener("click",()=>{$("#requestInput").value=b.dataset.example;}));