const plans = {
  sat: { title:'شنبه · قدرت کل بدن', type:'قدرت + شکم', exercises:[
    ['اسکوات','قدرت','🦵','۱۰ تکرار','۶۰ ثانیه','پاها کمی باز، کمر خنثی و حرکت را آرام انجام بده.','وزنه لازم نیست؛ فرم صحیح اولویت دارد.'],
    ['شنا روی تکیه‌گاه','سینه و دست','💪','۸–۱۲ تکرار','۶۰ ثانیه','دست‌ها کمی بازتر از شانه؛ بدن را یک‌تکه نگه دار.','اگر سخت بود، دست‌ها را روی دیوار یا میز محکم قرار بده.'],
    ['پل باسن','پا و لگن','🍑','۱۲ تکرار','۴۵ ثانیه','به پشت دراز بکش، زانوها خم و لگن را آرام بالا بیاور.','در بالاترین نقطه یک مکث کوتاه داشته باش.'],
    ['Bird Dog','عضلات مرکزی','🐕','۸ تکرار هر طرف','۳۰ ثانیه','دست و پای مخالف را آرام دراز کن و تعادل را نگه دار.','کمر را گود نکن و حرکت را آهسته انجام بده.'],
    ['پلانک','شکم','🧱','۲۰–۳۰ ثانیه','۴۵ ثانیه','آرنج زیر شانه و بدن در یک خط.','نفس را حبس نکن؛ آرام نفس بکش.'],
    ['راه رفتن سریع درجا','استقامت','🏃','۲ دقیقه','۳۰ ثانیه','دست‌ها را حرکت بده و ریتمی انتخاب کن که بتوانی کنترلش کنی.','هدف بالا بردن تدریجی ضربان قلب است، نه خستگی کامل.']
  ]},
  sun: { title:'یکشنبه · استقامت', type:'استقامت', exercises:[
    ['راه رفتن سریع درجا','استقامت','🚶','۶۰ ثانیه','۳۰ ثانیه','ریتم را کمی تندتر از راه رفتن عادی نگه دار.','در صورت نیاز، شدت را کمتر کن.'],
    ['دویدن آرام درجا','استقامت','🏃','۶۰ ثانیه','۶۰ ثانیه','گام‌های کوتاه و کنترل‌شده بردار.','لازم نیست سرعت زیاد باشد.'],
    ['Step Touch','استقامت','↔️','۶۰ ثانیه','۳۰ ثانیه','یک قدم به کنار و برگشت؛ دست‌ها را هم همراه کن.','حرکت را نرم و بدون پرش انجام بده.'],
    ['راه رفتن آرام','ریکاوری','🌿','۶۰ ثانیه','۳۰ ثانیه','سرعت را کم کن و نفس را منظم کن.','این بخش بین دورهای تمرین به ریکاوری کمک می‌کند.']
  ]},
  mon: { title:'دوشنبه · قدرت + شکم', type:'قدرت + شکم', exercises:[
    ['لانج معکوس','پاها','🦿','۸ تکرار هر پا','۶۰ ثانیه','یک پا را عقب ببر و با کنترل پایین برو.','برای حفظ تعادل می‌توانی کنار دیوار بایستی.'],
    ['شنا روی تکیه‌گاه','سینه و دست','💪','۸–۱۲ تکرار','۶۰ ثانیه','آرنج‌ها را خیلی باز نکن و بدن را یک‌تکه نگه دار.','سطح تکیه‌گاه را طوری انتخاب کن که فرم حفظ شود.'],
    ['اسکوات','پاها','🦵','۱۲ تکرار','۶۰ ثانیه','مثل نشستن روی صندلی، آرام پایین برو و بالا بیا.','زانوها هم‌جهت پنجه پا باشند.'],
    ['Dead Bug','شکم','🐞','۸ تکرار هر طرف','۳۰ ثانیه','به پشت، دست و پای مخالف را آهسته باز و جمع کن.','کمر را تا جای ممکن آرام و کنترل‌شده نگه دار.'],
    ['پلانک','شکم','🧱','۲۰–۳۰ ثانیه','۴۵ ثانیه','شانه‌ها بالای آرنج و شکم فعال.','کیفیت مهم‌تر از زمان طولانی است.']
  ]},
  tue: { title:'سه‌شنبه · روز سبک', type:'ریکاوری فعال', exercises:[
    ['پیاده‌روی آرام','ریکاوری','🚶','۱۰ دقیقه','۰ ثانیه','با ریتم راحت راه برو.','پیاده‌روی روزانه‌ات را هم می‌توانی در نظر بگیری.'],
    ['کشش آرام پاها','انعطاف','🧘','۳ دقیقه','۰ ثانیه','کشش باید ملایم باشد، نه دردناک.','بدن را با آرامش حرکت بده.'],
    ['تنفس آرام','ریکاوری','🌬️','۲ دقیقه','۰ ثانیه','آرام دم بگیر و بازدم را طولانی‌تر کن.','هدف کاهش سرعت و آماده شدن برای روز بعد است.']
  ]},
  wed: { title:'چهارشنبه · قدرت کل بدن', type:'قدرت + شکم', exercises:[
    ['اسکوات','قدرت','🦵','۱۰–۱۲ تکرار','۶۰ ثانیه','حرکت را آهسته و کنترل‌شده انجام بده.','فرم صحیح را حفظ کن.'],
    ['شنا روی تکیه‌گاه','سینه و دست','💪','۸–۱۲ تکرار','۶۰ ثانیه','بدن یک‌تکه و حرکت کامل اما کنترل‌شده.','در صورت نیاز آسان‌ترش کن.'],
    ['پل باسن','پا و لگن','🍑','۱۲ تکرار','۴۵ ثانیه','لگن را آرام بالا ببر و پایین بیاور.','حرکت را با فشار ناگهانی انجام نده.'],
    ['Bird Dog','مرکز بدن','🐕','۸ تکرار هر طرف','۳۰ ثانیه','دست و پای مخالف را دراز کن و تعادل را حفظ کن.','نگاه به زمین باشد.'],
    ['پلانک','شکم','🧱','۲۰–۳۰ ثانیه','۴۵ ثانیه','بدن در یک خط و تنفس طبیعی.','در صورت افت فرم، زودتر تمام کن.'],
    ['راه رفتن سریع درجا','استقامت','🏃','۲ دقیقه','۳۰ ثانیه','ریتم متوسط رو به تند.','هدف آمادگی بدنی است.']
  ]},
  thu: { title:'پنجشنبه · استقامت', type:'استقامت', exercises:[
    ['راه رفتن سریع درجا','استقامت','🚶','۶۰ ثانیه','۳۰ ثانیه','ریتم سریع اما قابل کنترل.','شانه‌ها را راحت نگه دار.'],
    ['دویدن آرام درجا','استقامت','🏃','۶۰ ثانیه','۶۰ ثانیه','گام‌های سبک و کوتاه.','پرش بلند لازم نیست.'],
    ['Step Touch','استقامت','↔️','۶۰ ثانیه','۳۰ ثانیه','حرکت کنار به کنار با دست‌ها.','فقط تا حدی که فرم خوب بماند.'],
    ['راه رفتن آرام','ریکاوری','🌿','۶۰ ثانیه','۳۰ ثانیه','تنفس را تنظیم کن و شدت را پایین بیاور.','در پایان، چند دقیقه آرام راه برو.']
  ]},
  fri: { title:'جمعه · ریکاوری', type:'استراحت فعال', exercises:[
    ['پیاده‌روی آرام','ریکاوری','🚶','۱۵ دقیقه','۰ ثانیه','با سرعتی راحت راه برو.','می‌تواند با پیاده‌روی عادی روزت ترکیب شود.'],
    ['کشش ملایم کل بدن','انعطاف','🧘','۵ دقیقه','۰ ثانیه','شانه، پشت، ران و ساق را آرام کشش بده.','هیچ کششی نباید دردناک باشد.']
  ]}
};

const dayButtons=document.querySelectorAll('.day');
const dayTitle=document.getElementById('dayTitle'),summaryType=document.getElementById('summaryType'),counter=document.getElementById('exerciseCounter'),progressBar=document.getElementById('progressBar');
const art=document.getElementById('exerciseEmoji'),category=document.getElementById('exerciseCategory'),name=document.getElementById('exerciseName'),hint=document.getElementById('exerciseHint');
const amount=document.getElementById('exerciseAmount'),rest=document.getElementById('restAmount'),setAmount=document.getElementById('setAmount'),timer=document.getElementById('timer'),timerLabel=document.getElementById('timerLabel');
const startBtn=document.getElementById('startBtn'),skipBtn=document.getElementById('skipBtn'),list=document.getElementById('exerciseList'),note=document.getElementById('coachNote'),toast=document.getElementById('toast'),streakValue=document.getElementById('streakValue');
let currentDay='sat',currentIndex=0,seconds=30,interval=null,running=false,completed=new Set();
const faDigits=v=>String(v).replace(/\d/g,d=>'۰۱۲۳۴۵۶۷۸۹'[d]);
const toLatinDigits=v=>String(v).replace(/[۰-۹]/g,d=>'۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
function formatTime(s){return `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;}
function showToast(msg){toast.textContent=msg;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),1800);}
function save(){localStorage.setItem('fitflow-progress',JSON.stringify({day:currentDay,completed:[...completed]}));}
function load(){try{const saved=JSON.parse(localStorage.getItem('fitflow-progress')||'{}');if(saved.day&&plans[saved.day])currentDay=saved.day;if(Array.isArray(saved.completed))completed=new Set(saved.completed);}catch(e){}streakValue.textContent=faDigits(localStorage.getItem('fitflow-streak')||0);}
function buildList(){list.innerHTML='';plans[currentDay].exercises.forEach((ex,i)=>{const li=document.createElement('li');if(i===currentIndex)li.classList.add('active');if(completed.has(`${currentDay}-${i}`))li.classList.add('done');li.innerHTML=`<span class="num">${faDigits(i+1)}</span><span>${ex[0]}</span>`;li.addEventListener('click',()=>goTo(i));list.appendChild(li);});}
function parseDuration(text){const clean=toLatinDigits(text);const minute=clean.match(/(\d+)\s*دقیقه/);if(minute)return Number(minute[1])*60;const sec=clean.match(/(\d+)\s*ثانیه/);if(sec)return Number(sec[1]);return 30;}
function resetTimer(){clearInterval(interval);interval=null;running=false;startBtn.textContent='شروع تایمر';const ex=plans[currentDay].exercises[currentIndex];seconds=parseDuration(ex[3]);timer.textContent=formatTime(seconds);timerLabel.textContent='آماده‌ای؟';}
function render(){const plan=plans[currentDay],ex=plan.exercises[currentIndex];dayTitle.textContent=plan.title;summaryType.textContent=plan.type;counter.textContent=`${faDigits(currentIndex+1)} / ${faDigits(plan.exercises.length)}`;progressBar.style.width=`${((currentIndex+1)/plan.exercises.length)*100}%`;art.textContent=ex[2];category.textContent=ex[1];name.textContent=ex[0];hint.textContent=ex[5];amount.textContent=ex[3];rest.textContent=ex[4];setAmount.textContent=`مرحله ${faDigits(currentIndex+1)} از ${faDigits(plan.exercises.length)}`;note.textContent=ex[6];resetTimer();buildList();}
function goTo(index){currentIndex=index;render();}
function finish(){completed.add(`${currentDay}-${currentIndex}`);save();buildList();if(currentIndex<plans[currentDay].exercises.length-1){showToast('عالی! حرکت بعدی آماده است 💪');currentIndex++;render();}else completeWorkout();}
function completeWorkout(){clearInterval(interval);running=false;startBtn.textContent='تمرین تمام شد';timerLabel.textContent='کارت عالی بود!';timer.textContent='✓';const old=Number(localStorage.getItem('fitflow-streak')||0),next=old+1;localStorage.setItem('fitflow-streak',String(next));streakValue.textContent=faDigits(next);showToast('تمرین امروز کامل شد 🎉');buildList();}
startBtn.addEventListener('click',()=>{if(running)return;running=true;startBtn.textContent='در حال اجرا…';timerLabel.textContent='زمان تمرین';clearInterval(interval);interval=setInterval(()=>{seconds--;timer.textContent=formatTime(Math.max(seconds,0));if(seconds<=0)finish();},1000);});
skipBtn.addEventListener('click',finish);
dayButtons.forEach(btn=>btn.addEventListener('click',()=>{dayButtons.forEach(x=>x.classList.remove('active'));btn.classList.add('active');currentDay=btn.dataset.day;currentIndex=0;completed=new Set();save();render();}));
load();dayButtons.forEach(btn=>btn.classList.toggle('active',btn.dataset.day===currentDay));render();
