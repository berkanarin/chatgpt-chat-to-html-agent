const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {JSDOM,VirtualConsole,requestInterceptor}=require('jsdom');
const root=path.resolve(__dirname,'..');
const demo=path.join(root,'work/demo/demo.html');
if(!fs.existsSync(demo))execFileSync(process.env.PYTHON||'python',['examples/create_demo.py','--output','work/demo'],{cwd:root});
const source=fs.readFileSync(demo,'utf8');
const original=JSON.parse(source.match(/id="conversation-data">(.*?)<\/script>/s)[1]);
const wait=(ms=80)=>new Promise(r=>setTimeout(r,ms));
function mount(data=structuredClone(original),options={}){
 const errors=[],scrolls=[],downloads=[],network=[];
 const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const intercept=requestInterceptor(request=>{network.push(request.url);return new Response('',{status:200});});
 const content=source.replace(/(id="conversation-data">).*?(<\/script>)/s,(_,a,b)=>a+JSON.stringify(data).replace(/</g,'\\u003c')+b);
 let mobile=!!options.mobile;
 const dom=new JSDOM(content,{runScripts:'dangerously',pretendToBeVisual:true,virtualConsole:vc,resources:{interceptors:[intercept]},beforeParse(w){
  w.innerHeight=options.height||900;
  w.matchMedia=q=>({matches:q.includes('max-width')?mobile:options.reduced!==false});
  w.scrollTo=o=>{scrolls.push(o);w.scrollY=o.top;};
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  w.HTMLAnchorElement.prototype.click=function(){downloads.push({name:this.download,href:this.href});};
  w.HTMLElement.prototype.getBoundingClientRect=function(){
   let top=0,height=0;
   if(this.classList.contains('topbar'))height=70;
   if(this.classList.contains('learning-rail'))height=180;
   if(this.classList.contains('composer-wrap')){height=220;top=w.innerHeight-height;}
   if(this.classList.contains('message')&&this.querySelector('.answer')){top=1200-w.scrollY;height=500;}
   return {top,bottom:top+height,height,left:0,right:600,width:600};
  };
 }});
 const w=dom.window,d=w.document,id=x=>d.getElementById(x);
 return {w,d,id,errors,scrolls,downloads,network,setMobile:v=>{mobile=v;},close:()=>{assert.deepEqual(errors,[]);assert.deepEqual(network,[]);w.close();}};
}

test('three-turn replay, no future reveal, keyboard, cards and completion',async()=>{
 const a=mount();try{
  assert.equal(a.d.querySelectorAll('.turn').length,0);
  assert.equal(a.d.querySelector('.intro'),null);
  assert.equal(a.d.querySelectorAll('.step').length,3);
  a.id('send').click();a.id('send').click();await wait();
  assert.equal(a.d.querySelectorAll('.turn').length,1);
  assert.equal(a.id('lesson-title').textContent,original.steps[0].lessonTitle);
  a.id('prompt').dispatchEvent(new a.w.KeyboardEvent('keydown',{key:'Enter',bubbles:true,cancelable:true}));await wait();
  assert.equal(a.d.querySelectorAll('.turn').length,2);
  a.id('lesson-prev').click();assert.equal(a.id('lesson-title').textContent,original.steps[0].lessonTitle);
  a.id('lesson-next').click();assert.equal(a.id('lesson-title').textContent,original.steps[1].lessonTitle);
  a.id('send').click();await wait();
  assert.equal(a.id('send').disabled,true);
  assert.equal(a.id('side-progress').textContent,'3 / 3 adım tamamlandı');
  assert.equal(a.id('final-compare').hidden,true,'text-only final turn has no fake comparison');
  assert.ok(a.d.querySelector('.answer table'));
  a.d.querySelector('[data-lesson="0"]').click();assert.equal(a.id('lesson-title').textContent,original.steps[0].lessonTitle);
 }finally{a.close();}
});

test('image zoom, explicit comparison, wipe and original attachment download',async()=>{
 const a=mount();try{
  a.id('send').click();await wait();a.id('send').click();await wait();
  assert.equal(a.d.querySelectorAll('[data-compare]').length,1);
  a.d.querySelector('[data-image]').click();assert.ok(a.id('viewer').open);
  a.id('zoom-stage').click();assert.ok(a.id('zoom-stage').classList.contains('actual'));
  a.id('close-modal').click();
  a.d.querySelector('[data-compare]').click();
  assert.equal(a.d.querySelectorAll('#pair img').length,2);
  a.id('wipe-tab').click();a.id('wipe-range').value='75';a.id('wipe-range').dispatchEvent(new a.w.Event('input'));
  assert.equal(a.id('wipe-top').style.clipPath,'inset(0 25% 0 0)');
  a.id('close-modal').click();a.id('send').click();await wait();
  a.d.querySelector('[data-file]').click();
  assert.equal(a.downloads[0].name,'Değişiklikler.csv');
  const ref=original.steps[2].files[0];assert.equal(a.downloads[0].href,original.assets[ref.id].data);
 }finally{a.close();}
});

test('follow waits for response and clears desktop/mobile overlays',async()=>{
 const a=mount();try{
  a.id('send').click();assert.equal(a.scrolls.length,0);await wait();
  assert.equal(a.scrolls.length,1);assert.equal(a.scrolls[0].top,1114);assert.equal(a.scrolls[0].behavior,'instant');
  assert.equal(a.d.documentElement.style.getPropertyValue('--response-image-height'),'470px');
  a.setMobile(true);a.w.innerHeight=700;a.w.dispatchEvent(new a.w.Event('resize'));
  a.id('send').click();await wait();
  assert.equal(a.scrolls.at(-1).top,1004);
  assert.equal(a.d.documentElement.style.getPropertyValue('--response-image-height'),'175px');
  const n=a.scrolls.length;a.id('send').click();a.w.dispatchEvent(new a.w.Event('wheel'));await wait();
  assert.equal(a.scrolls.length,n,'manual navigation cancels pending follow');
 }finally{a.close();}
});

test('reset cancels pending response and follow; mobile card disclosure works',async()=>{
 const a=mount();try{
  a.id('lesson-toggle').click();assert.equal(a.id('lesson-toggle').getAttribute('aria-expanded'),'true');
  a.id('lesson-toggle').click();assert.equal(a.id('lesson-toggle').getAttribute('aria-expanded'),'false');
  a.id('send').click();a.id('reset').click();a.id('confirm-reset').click();await wait();
  assert.equal(a.d.querySelectorAll('.turn').length,0);assert.equal(a.id('lesson-counter').textContent,'0 / 3 kart açıldı');
  assert.equal(a.id('send').disabled,false);assert.equal(a.scrolls.length,1,'only reset scroll is allowed');
 }finally{a.close();}
});

test('one and twelve steps have dynamic totals and correct finish',async()=>{
 for(const count of [1,12]){
  const data=structuredClone(original);data.steps=Array.from({length:count},(_,i)=>({...structuredClone(original.steps[0]),id:`step-${i+1}`,compareTo:null}));
  const a=mount(data);try{
   for(let i=0;i<count;i++){a.id('send').click();await wait(45);}
   assert.equal(a.d.querySelectorAll('.turn').length,count);
   assert.equal(a.id('side-progress').textContent,`${count} / ${count} adım tamamlandı`);
   assert.equal(a.id('send').disabled,true);
  }finally{a.close();}
 }
});

test('long prompt, recorded choice and aspect-ratio guard',async()=>{
 const data=structuredClone(original);data.steps[0].prompt='uzun komut '.repeat(150);
 data.steps[0].choice={options:['Kapak','Kapanış'],selected:1};
 data.steps[1].images[0].width=540;data.steps[1].images[0].height=960;
 const a=mount(data);try{
  a.id('full-prompt').click();assert.ok(a.id('modal-body').textContent.includes(data.steps[0].prompt));a.id('close-modal').click();
  a.id('send').click();await wait();assert.equal(a.d.querySelectorAll('.choice input:checked').length,1);
  a.id('send').click();await wait();a.d.querySelector('[data-compare]').click();assert.equal(a.id('wipe-tab').hidden,true);
 }finally{a.close();}
});

test('scroll-reading selects the visible lesson; spring stays interruptible',async()=>{
 const a=mount(undefined,{reduced:false});try{
  a.id('send').click();await wait();a.id('send').click();await wait();
  a.id('lesson-prev').click();a.id('lesson-next').click();assert.equal(a.id('lesson-title').textContent,original.steps[1].lessonTitle);
  const now=a.w.Date.now;a.w.Date.now=()=>now()+3000;
  a.d.querySelectorAll('.turn').forEach((node,i)=>{node.getBoundingClientRect=()=>i===0?{top:100,bottom:600}:{top:-500,bottom:-100};});
  a.w.dispatchEvent(new a.w.Event('scroll'));await wait();assert.equal(a.id('lesson-title').textContent,original.steps[0].lessonTitle);
  await wait(800);assert.equal(a.id('lesson-card').style.transform,'');
 }finally{a.close();}
});
