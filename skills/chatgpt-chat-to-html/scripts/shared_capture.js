'use strict';

// Pass this function to the host browser tool's READ-ONLY evaluate API.
// No fetch, hidden application state, cookies, DOM writes or transcript execution.
function captureSnapshot() {
 const headings=Array.from(document.querySelectorAll('h4[data-conversation-role]'));
 const issues=[];
 const messages=headings.map(h=>{
  const root=h.parentElement,role=h.getAttribute('data-conversation-role');
  const idNode=root.matches('[data-chatgpt-search-message-ids]')?root:root.querySelector('[data-chatgpt-search-message-ids]');
  const id=idNode?.getAttribute('data-chatgpt-search-message-ids')?.split(' ')[0];
  if(!id)issues.push('missing_message_id');
  const bubble=root.querySelector('[data-user-message-bubble] .whitespace-pre-wrap');
  // ChatGPT renders inline backticks as <code> even inside its raw-looking
  // user bubble. textContent alone silently loses the delimiters.
  const userText=node=>{
   if(node.nodeType===3)return node.textContent;
   if(node.nodeType!==1)return '';
   if(node.tagName==='BR')return '\n';
   if(node.tagName==='CODE'){
    const value=node.textContent;
    const ticks='`'.repeat(Math.max(0,...(value.match(/`+/g)||[]).map(s=>s.length))+1);
    const pad=value.startsWith('`')||value.endsWith('`')?' ':'';
    return ticks+pad+value+pad+ticks;
   }
   if(!['DIV','SPAN'].includes(node.tagName))issues.push('review_user_markup:'+id+':'+node.tagName);
   return Array.from(node.childNodes).map(userText).join('');
  };
  const textNodes=Array.from(root.querySelectorAll('[data-markdown-text-style="assistant-message"]'));
  let text=role==='user'?(bubble?userText(bubble):''):textNodes.map(n=>n.innerText).join('\n\n');
  // Preserve visible recorded UI labels as inert text; selected controls are NOT
  // evidence of historical choices. The agent reviews them against the next turn.
  const options=Array.from(root.querySelectorAll('[role="radio"],input[type="radio"]'));
  const choices=options.map(n=>n.getAttribute('aria-label')||n.closest('label')?.innerText||n.parentElement?.innerText||'').filter(Boolean);
  const missingChoices=[...new Set(choices)].filter(label=>!text.split('\n').some(line=>line.trim()===label.trim()));
  if(missingChoices.length)text+='\n\n'+missingChoices.join('\n');
  if(role==='user'&&!bubble)issues.push('missing_user_text:'+id);
  if(root.querySelector('iframe,video,audio,canvas'))issues.push('unsupported_embed:'+id);
  const sourceKey=value=>{const u=new URL(value,document.baseURI);return u.pathname+(u.searchParams.get('id')?'?id='+u.searchParams.get('id'):'');};
  const media=Array.from(root.querySelectorAll('img')).map((im,i)=>({
   id:id+':image:'+i,kind:'image',name:im.alt||'Görsel',url:im.currentSrc||im.src,
   sourceKey:sourceKey(im.currentSrc||im.src),
   width:im.naturalWidth,height:im.naturalHeight
  }));
  for(const a of root.querySelectorAll('a[download]'))media.push({id:id+':file:'+media.length,kind:'file',name:a.download||a.textContent,url:a.href,sourceKey:sourceKey(a.href)});
  // Unknown attachment buttons cannot be silently declared captured.
  for(const button of root.querySelectorAll('[aria-label]')){
   if(/attachment|kullanıcı eki/i.test(button.getAttribute('aria-label'))&&!button.querySelector('img')&&button.tagName!=='IMG')issues.push('review_attachment:'+id);
  }
  if(!text.trim()&&!media.length)issues.push('empty_message:'+id);
  return {id,role,text:text.trim(),format:role==='user'?'markdown':'plain',media};
 });
 let region=headings[0];
 while(region&&!(region.scrollHeight>region.clientHeight+5&&region.clientHeight>100&&/auto|scroll/.test(getComputedStyle(region).overflowY)))region=region.parentElement;
 return {messages,issues,atTop:!!region&&region.scrollTop<=2,
  atBottom:!!region&&region.scrollHeight-region.clientHeight-region.scrollTop<=2};
}

// Virtualized views may retain a distant last message. Merge observed order
// constraints, not array offsets or a count from one viewport.
function mergeSnapshots(snapshots) {
 const nodes=new Map(),edges=new Map(),issues=new Set();
 for(const snapshot of snapshots){
  for(const issue of snapshot.issues||[])issues.add(issue);
  let previous=null;
  for(const m of snapshot.messages){
   if(!m.id)throw Error('A stable message ID is required');
   const old=nodes.get(m.id);
   if(old&&(old.role!==m.role||old.format!==m.format||(old.text&&m.text&&old.text!==m.text)))throw Error('Message changed during capture: '+m.id);
   const media=new Map((old?.media||[]).map(a=>[a.id,a]));
   for(const item of m.media){
    const prior=media.get(item.id);
    if(prior&&(prior.kind!==item.kind||prior.name!==item.name||(prior.sourceKey&&item.sourceKey&&prior.sourceKey!==item.sourceKey)))throw Error('Media changed during capture: '+item.id);
    media.set(item.id,{...prior,...item,width:item.width||prior?.width,height:item.height||prior?.height});
   }
   nodes.set(m.id,{...m,text:m.text||old?.text||'',media:[...media.values()]});if(!edges.has(m.id))edges.set(m.id,new Set());
   if(previous)edges.get(previous).add(m.id);previous=m.id;
  }
 }
 const degree=new Map([...nodes.keys()].map(id=>[id,0]));
 for(const next of edges.values())for(const id of next)degree.set(id,degree.get(id)+1);
 const ordered=[];
 while(ordered.length<nodes.size){
  const available=[...degree].filter(([,d])=>d===0).map(([id])=>id);
  if(available.length!==1)throw Error('Missing overlap, conflicting order or duplicate IDs; scan again');
  const id=available[0];ordered.push(nodes.get(id));degree.set(id,-1);
  for(const next of edges.get(id))degree.set(next,degree.get(next)-1);
 }
 for(const m of ordered){
  if(m.text||m.media.length)issues.delete('empty_message:'+m.id);
  if(m.role==='user'&&m.text)issues.delete('missing_user_text:'+m.id);
 }
 return {messages:ordered,issues:[...issues],reachedTop:snapshots.some(s=>s.atTop),reachedBottom:snapshots.some(s=>s.atBottom),
  messageIds:ordered.map(m=>m.id),mediaIds:ordered.flatMap(m=>m.media.map(a=>a.id))};
}

// Host-provided driver uses its authorized browser/download tools. Every retry
// reopens the original share and locates the SAME message/media, never retries
// a signed URL or substitutes a neighboring image. Verification includes bytes.
async function recoverMedia(items,driver,maxAttempts=3){
 if(!Number.isInteger(maxAttempts)||maxAttempts<1||maxAttempts>3)throw Error('Use 1–3 attempts');
 const results=[];
 for(const item of items){
  let result={id:item.id,status:'missing',attempts:0};
  for(let attempt=1;attempt<=maxAttempts;attempt++){
   result.attempts=attempt;
   try{
    if(attempt>1)await driver.refreshSource();
    const current=await driver.locate(item.id);
    if(!current||current.id!==item.id||(item.sourceKey&&current.sourceKey!==item.sourceKey))throw Error('media_identity_changed');
    const path=await driver.download(current);
    const verified=await driver.verify(path,item);
    if(!verified)throw Error('invalid_download');
    result={...result,status:'ready',path,...verified};break;
   }catch(error){
    // Never serialize signed URLs, auth headers, or raw browser errors.
    result.status='missing';
    result.reason=error.code==='ACCESS_DENIED'?'access_denied':'download_or_verification_failed';
    if(error.code==='ACCESS_DENIED')break;
   }
  }
  results.push(result);
 }
 return results;
}

if(typeof module!=='undefined')module.exports={captureSnapshot,mergeSnapshots,recoverMedia};
