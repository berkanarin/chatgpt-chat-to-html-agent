const DATA = JSON.parse(document.getElementById("conversation-data").textContent);
const TOTAL=DATA.steps.length;
let completed=0, busy=false, generation=0, lessonIndex=-1, lessonScrollLock=0, followTicket=0;
const $=id=>document.getElementById(id);
const esc=text=>String(text).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const img=(item,extra='')=>`<img src="${DATA.assets[item.id].data}" alt="${esc(item.alt)}" width="${item.width}" height="${item.height}" ${extra}>`;
const rich=text=>esc(text).replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>');
const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
function chatViewport(){
 const mobile=matchMedia('(max-width: 760px)').matches;
 const top=mobile?(document.querySelector('.learning-rail')?.getBoundingClientRect().height||0):(document.querySelector('.topbar')?.getBoundingClientRect().height||0);
 const bottom=document.querySelector('.composer-wrap')?.getBoundingClientRect().height||0;
 return {top,bottom,height:window.visualViewport?.height||innerHeight};
}
function sizeResponseImages(){
 const v=chatViewport();
 document.documentElement.style.setProperty('--response-image-height',Math.max(110,Math.min(470,v.height-v.top-v.bottom-125))+'px');
}
function scrollToNode(node){
 if(!node?.isConnected)return;
 const top=Math.max(0,window.scrollY+node.getBoundingClientRect().top-chatViewport().top-16);
 lessonScrollLock=Date.now()+1200;
 window.scrollTo({top,behavior:reduced()?'instant':'smooth'});
}
function followResponse(turn,ticket){
 // Run after the answer, composer and reserved image dimensions enter layout.
 requestAnimationFrame(()=>{
  if(ticket!==followTicket||!turn.isConnected)return;
  sizeResponseImages();
  const answer=turn.querySelector('.answer');
  scrollToNode(answer?.closest('.message')||turn);
 });
}
window.addEventListener('resize',sizeResponseImages,{passive:true});
window.visualViewport?.addEventListener('resize',sizeResponseImages,{passive:true});
// A pending follow must never pull the reader back after manual navigation.
window.addEventListener('wheel',()=>{followTicket++;},{passive:true});
window.addEventListener('touchstart',()=>{followTicket++;},{passive:true});
window.addEventListener('keydown',e=>{if(['PageUp','PageDown','Home','End','ArrowUp','ArrowDown'].includes(e.key))followTicket++;});
const lessonTitles=DATA.steps.map(s=>s.lessonTitle||s.title);
const learningRail=document.createElement('aside');
learningRail.className='learning-rail';learningRail.setAttribute('aria-label','Öğrenme kartları');
learningRail.innerHTML=`<div class="learning-header"><div><div class="eyebrow">Atölye notları</div><h2>Bu adım ne öğretiyor?</h2></div><button class="lesson-toggle" id="lesson-toggle" aria-expanded="false" aria-controls="lesson-copy">Kartı aç ↓</button></div><div class="lesson-deck"><div class="card-back one" aria-hidden="true"></div><div class="card-back two" aria-hidden="true"></div><div class="card-back three" aria-hidden="true"></div><article class="lesson-card" id="lesson-card" aria-live="polite" aria-atomic="true"><div class="card-top"><span id="lesson-kicker">Öğrenme kartları</span><span class="card-symbol" aria-hidden="true">✳</span></div><h3 id="lesson-title"></h3><p class="lesson-copy" id="lesson-copy"></p><div class="lesson-bottom"><span id="lesson-step"></span><button class="lesson-jump" id="lesson-jump" hidden>Sohbette göster ↗</button></div></article></div><div class="lesson-controls"><span class="lesson-counter" id="lesson-counter"></span><div class="card-arrows"><button class="card-arrow" id="lesson-prev" aria-label="Önceki öğrenme kartı">←</button><button class="card-arrow" id="lesson-next" aria-label="Sonraki öğrenme kartı">→</button></div></div><div class="lesson-dots" id="lesson-dots" aria-label="Kart seçimi"></div><p class="lesson-context">Sohbete eşlik eden eğitim notları.</p>`;
document.querySelector('.shell').append(learningRail);
// A critically damped spring retains its position and velocity on repeated input.
const cardMotion={y:0,v:0,frame:0,last:0};
function stopLessonMotion(){
 cancelAnimationFrame(cardMotion.frame);Object.assign(cardMotion,{y:0,v:0,frame:0,last:0});$('lesson-card').style.transform='';
}
function settleLesson(){
 if(reduced()){stopLessonMotion();return;}
 if(!cardMotion.frame){cardMotion.y=7;cardMotion.last=performance.now();cardMotion.frame=requestAnimationFrame(tickLesson);}
}
function tickLesson(now){
 if(reduced()){stopLessonMotion();return;}
 const dt=Math.min((now-cardMotion.last)/1000,.032);cardMotion.last=now;
 const omega=22;
 cardMotion.v+=(-omega*omega*cardMotion.y-2*omega*cardMotion.v)*dt;
 cardMotion.y+=cardMotion.v*dt;
 $('lesson-card').style.transform=`translate3d(0,${cardMotion.y}px,0)`;
 if(Math.abs(cardMotion.y)<.025&&Math.abs(cardMotion.v)<.1){stopLessonMotion();return;}
 cardMotion.frame=requestAnimationFrame(tickLesson);
}

function renderLesson(animate=false){
 const s=DATA.steps[lessonIndex];
 $('lesson-kicker').textContent=s?`KART ${String(lessonIndex+1).padStart(2,'0')} / ${String(TOTAL).padStart(2,'0')}`:'Öğrenme kartları';
 $('lesson-title').textContent=s?lessonTitles[lessonIndex]:'Adım adım öğren.';
 $('lesson-copy').textContent=s?(s.note||'Bu adım için eğitim notu eklenmemiş.'):'Komutu gönderdiğinde bu adımın notu burada açılır.';
 $('lesson-step').textContent=s?s.title:'Henüz başlamadın';
 $('lesson-jump').hidden=!s;
 $('lesson-counter').textContent=s?`${lessonIndex+1} / ${completed} açık kart`:`0 / ${TOTAL} kart açıldı`;
 $('lesson-prev').disabled=lessonIndex<=0;
 $('lesson-next').disabled=lessonIndex<0||lessonIndex>=completed-1;
 $('lesson-dots').innerHTML=DATA.steps.map((s,i)=>`<button class="lesson-dot" data-lesson="${i}" aria-label="${i+1}. kart: ${esc(lessonTitles[i])}" aria-pressed="${i===lessonIndex}" ${i>=completed?'disabled':''}></button>`).join('');
 document.querySelectorAll('.step').forEach(b=>b.classList.toggle('inspecting',Number(b.dataset.step)===lessonIndex));
 if(animate)settleLesson();
}
function selectLesson(index,jump=false){
 if(index<0||index>=completed)return;
 const changed=index!==lessonIndex;lessonIndex=index;renderLesson(changed);
 if(jump){followTicket++;lessonScrollLock=Date.now()+1200;scrollToNode($('turn-'+index));}
}
$('lesson-prev').onclick=()=>selectLesson(lessonIndex-1);
$('lesson-next').onclick=()=>selectLesson(lessonIndex+1);
$('lesson-dots').onclick=e=>{const b=e.target.closest('[data-lesson]');if(b&&!b.disabled)selectLesson(Number(b.dataset.lesson));};
$('lesson-jump').onclick=()=>selectLesson(lessonIndex,true);
$('lesson-toggle').onclick=()=>{const expanded=learningRail.classList.toggle('expanded');$('lesson-toggle').setAttribute('aria-expanded',String(expanded));$('lesson-toggle').textContent=expanded?'Kartı kapat ↑':'Kartı aç ↓';sizeResponseImages();};
let lessonFrame=false;
window.addEventListener('scroll',()=>{if(lessonFrame)return;lessonFrame=true;requestAnimationFrame(()=>{lessonFrame=false;if(busy||Date.now()<lessonScrollLock||!completed)return;const line=matchMedia('(max-width: 760px)').matches?learningRail.getBoundingClientRect().bottom+45:Math.min(260,innerHeight*.35);for(let i=completed-1;i>=0;i--){const r=$('turn-'+i).getBoundingClientRect();if(r.top<=line&&r.bottom>line){if(i!==lessonIndex)selectLesson(i);break;}}});},{passive:true});
function update(){
 $('steps').innerHTML=DATA.steps.map((s,i)=>`<li><button class="step ${i<completed?'done':i===completed?'current':''}" data-step="${i}" ${i>=completed?'disabled':''} ${i===completed?'aria-current="step"':''}><span class="num">${i<completed?'✓':String(i+1).padStart(2,'0')}</span><span>${esc(s.title)}</span></button></li>`).join('');
 $('side-progress').textContent=`${completed} / ${TOTAL} adım tamamlandı`;$('progress-fill').style.width=(completed/TOTAL*100)+'%';
 $('progress-label').textContent=busy?'Yanıt gösteriliyor…':completed===TOTAL?'Tamamlandı':`${completed} / ${TOTAL} tamamlandı`;
 $('next-label').textContent=completed===TOTAL?'Sohbet tamamlandı':`Komut · ${String(completed+1).padStart(2,'0')} / ${String(TOTAL).padStart(2,'0')}`;
 const step=DATA.steps[completed];
 $('prompt').value=step?(step.prompt.length>700?step.prompt.slice(0,370)+'\n\n… Komutun tamamını yukarıdaki bağlantıdan inceleyebilirsin.':step.prompt):'Sohbet tamamlandı. Görselleri ve karşılaştırmaları dilediğin zaman yeniden inceleyebilirsin.';
 $('full-prompt').hidden=!step||step.prompt.length<700;
 $('send').disabled=busy||completed===TOTAL;
 $('send').firstElementChild.textContent=busy?'Bekle':completed===TOTAL?'Tamamlandı':'Gönder';
 $('composer-hint').textContent=step?.attachments.length?`${step.attachments.length} görsel referansı ekli`:'Enter ile gönder';
 $('finish').hidden=completed!==TOTAL;
 $('final-compare').hidden=!previousImage(TOTAL-1);
 renderLesson();
 sizeResponseImages();
}
function userHTML(s){return `<div class="message"><div class="role"><span class="avatar user">S</span>Sen <small>Özgün komut</small></div><div class="bubble">${s.prompt.length>700?`<details class="prompt-details"><summary>Uzun komut · tamamını göster</summary><pre class="prompt-text">${esc(s.prompt)}</pre></details><div class="prompt-text">${esc(s.prompt.slice(0,160))}…</div>`:`<pre class="prompt-text">${esc(s.prompt)}</pre>`}${fileHTML(s.userFiles)}${s.attachments.map(a=>`<button class="attachment" data-image="${a.id}" data-alt="${esc(a.alt)}">${img(a)}<span>${esc(a.name)}<br>Ekli referansı büyüt ↗</span></button>`).join('')}</div></div>`;}
function previousImage(i){const k=DATA.steps.findIndex(s=>s.id===DATA.steps[i].compareTo);return k>=0&&k<i&&DATA.steps[k].images.length?{index:k,item:DATA.steps[k].images[0]}:null;}

function choiceHTML(choice){
 return `<div class="choice" role="group" aria-label="Kayıttaki seçim">${choice.options.map((option,i)=>`<label class="choice-label ${i===choice.selected?'':'off'}"><input type="radio" disabled ${i===choice.selected?'checked':''}> ${esc(option)}</label>`).join('')}<small>Kayıtta seçilen seçenek gösteriliyor.</small></div>`;
}
function fileHTML(files){return (files||[]).map(f=>`<button class="file-download" data-file="${f.id}" data-name="${esc(f.name)}"><span aria-hidden="true">↓</span> ${esc(f.name)}</button>`).join('');}
function downloadFile(id,name){const a=document.createElement('a');a.href=DATA.assets[id].data;a.download=name;document.body.append(a);a.click();a.remove();}

function answerHTML(s,i){return `<div class="message"><div class="role"><span class="avatar">✳</span>ChatGPT <small>Kayıttaki yanıt</small></div><div class="answer">${s.answerHtml||(!s.images.length&&!s.files.length?'<p>Bu adımın yanıtı arşivde bulunmuyor.</p>':'')}${s.choice?choiceHTML(s.choice):''}${fileHTML(s.files)}${s.images.map(a=>`<figure class="figure"><button class="image-button ${a.height>a.width?'portrait':''}" data-image="${a.id}" data-alt="${esc(a.alt)}" aria-label="${esc(a.alt)} — görseli büyüt">${img(a,'decoding="async"')}<span class="zoom-tag">Büyüt ↗</span></button><figcaption class="figure-footer"><span>${esc(a.alt)}</span>${previousImage(i)?`<button class="compare-button" data-compare="${i}">Öncekiyle karşılaştır ↔</button>`:'<span>Özgün görsel</span>'}</figcaption></figure>`).join('')}</div></div>`;}
async function advance(e){e?.preventDefault();if(busy||completed>=DATA.steps.length)return;busy=true;const token=generation,ticket=++followTicket;const i=completed,s=DATA.steps[i];$('welcome').hidden=true;const turn=document.createElement('section');turn.className='turn';turn.id='turn-'+i;turn.innerHTML=`<div class="turn-heading"><b>ADIM ${String(i+1).padStart(2,'0')}</b>${esc(s.title)}</div>${userHTML(s)}<div class="pending" role="status">Kayıttaki yanıt açılıyor</div>`;$('conversation').append(turn);update();await new Promise(requestAnimationFrame);if(token!==generation)return;turn.querySelector('.pending').remove();turn.insertAdjacentHTML('beforeend',answerHTML(s,i));completed++;busy=false;lessonIndex=i;lessonScrollLock=Date.now()+900;update();renderLesson(true);followResponse(turn,ticket);$('status').textContent=`${i+1}. adım açıldı: ${s.title}`;}
function modal(title,html,small=false){$('viewer').classList.toggle('small-dialog',small);$('modal-title').textContent=title;$('modal-body').innerHTML=html;$('viewer').showModal();}
function zoom(id,alt){modal(alt,`<div class="zoom-stage" id="zoom-stage"><img src="${DATA.assets[id].data}" alt="${esc(alt)}"></div><div class="zoom-help">Görsele tıklayarak gerçek boyut / ekrana sığdır arasında geçiş yap. Esc ile kapat.</div>`);$('zoom-stage').onclick=()=>{$('zoom-stage').classList.toggle('actual');};}
function compare(i){const prev=previousImage(i),s=DATA.steps[i],a=s.images[0];if(!prev||!a)return;
 modal('Değişimi incele',`<div class="compare-tools"><div class="tabs" aria-label="Karşılaştırma görünümü"><button id="side-tab" aria-pressed="true">Yan yana</button><button id="wipe-tab" aria-pressed="false">Kaydırarak</button></div><span class="compare-label">${esc(prev.index+1+'. adım')} → <strong>${esc(i+1+'. adım')}</strong></span></div><div id="pair" class="compare-pair"><div><span class="compare-label">ÖNCE · ${esc(DATA.steps[prev.index].title)}</span>${img(prev.item)}</div><div><span class="compare-label">SONRA · ${esc(s.title)}</span>${img(a)}</div></div><div id="wipe-view" hidden><div class="wipe">${img(a)}<div class="wipe-top" id="wipe-top">${img(prev.item)}</div><div class="wipe-line" id="wipe-line"></div></div><label class="range-wrap">Önce <input id="wipe-range" aria-label="Önceki görselin görünürlük oranı" type="range" min="0" max="100" value="50"> Sonra</label></div><div class="zoom-help">Komut: “${esc(s.prompt)}”</div>`);
 const sameRatio=Math.abs(prev.item.width/prev.item.height-a.width/a.height)<.02;$('wipe-tab').hidden=!sameRatio;
 const mode=wipe=>{$('pair').hidden=wipe;$('wipe-view').hidden=!wipe;$('side-tab').setAttribute('aria-pressed',String(!wipe));$('wipe-tab').setAttribute('aria-pressed',String(wipe));};$('side-tab').onclick=()=>mode(false);$('wipe-tab').onclick=()=>mode(true);$('wipe-range').oninput=e=>{const n=e.target.value;$('wipe-top').style.clipPath=`inset(0 ${100-n}% 0 0)`;$('wipe-line').style.left=n+'%';};
}
function reset(){stopLessonMotion();followTicket++;generation++;completed=0;busy=false;lessonIndex=-1;lessonScrollLock=0;$('conversation').replaceChildren();$('welcome').hidden=false;update();window.scrollTo({top:0,behavior:reduced()?'instant':'smooth'});$('status').textContent='Sohbet başa döndü.';}
$('composer').addEventListener('submit',advance);$('prompt').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();advance();}});
$('full-prompt').onclick=()=>{const s=DATA.steps[completed];if(s)modal('Komut · özgün metin',`<pre class="modal-prompt">${esc(s.prompt)}</pre>`);};
$('steps').onclick=e=>{const b=e.target.closest('[data-step]');if(b&&!b.disabled)selectLesson(Number(b.dataset.step),true);};
$('conversation').onclick=e=>{const b=e.target.closest('[data-image]');if(b)zoom(b.dataset.image,b.dataset.alt);const f=e.target.closest('[data-file]');if(f)downloadFile(f.dataset.file,f.dataset.name);const c=e.target.closest('[data-compare]');if(c)compare(Number(c.dataset.compare));};
$('final-compare').onclick=()=>compare(TOTAL-1);
$('reset').onclick=()=>{if(!completed&&!busy)return;modal('Sohbet başa dönsün mü?',`<div class="reset-copy">Adımlar kapanacak ve ilk komuttan başlayacaksın.<div class="reset-actions"><button class="compare-button" id="cancel-reset">Vazgeç</button><button class="send" id="confirm-reset">Başa dön</button></div></div>`,true);$('cancel-reset').onclick=()=>$('viewer').close();$('confirm-reset').onclick=()=>{$('viewer').close();reset();};};
$('close-modal').onclick=()=>$('viewer').close();$('viewer').addEventListener('click',e=>{if(e.target===$('viewer')){const r=$('viewer').getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$('viewer').close();}});
update();

if(DATA.audit.problems.length){
 const banner=document.createElement('details');banner.className='archive-warning';
 banner.innerHTML=`<summary>${DATA.audit.problems.length} dışa aktarım uyarısı</summary><ul>${DATA.audit.problems.map(p=>`<li>${esc(p.step)}: ${esc(p.kind)} — ${esc(p.target)}</li>`).join('')}</ul>`;
 document.querySelector('.content').prepend(banner);
}
