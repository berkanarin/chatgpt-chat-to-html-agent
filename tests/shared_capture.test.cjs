const {test}=require('node:test');
const assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const {captureSnapshot,mergeSnapshots,recoverMedia}=require('../skills/chatgpt-chat-to-html/scripts/shared_capture.js');
const m=(id,role='assistant',media=[])=>({id,role,text:id,format:'plain',media});
test('virtualized overlapping snapshots preserve order and reject ambiguity/conflicts',()=>{
 const u=m('u','user'),a=m('a'),v=m('v','user'),b=m('b');
 const merged=mergeSnapshots([{atBottom:true,messages:[a,v,b]},{atTop:true,messages:[u,a,b]}]);
 assert.deepEqual(merged.messageIds,['u','a','v','b']);assert.ok(merged.reachedTop&&merged.reachedBottom);
 assert.throws(()=>mergeSnapshots([{messages:[u,a]},{messages:[v,b]}]),/overlap/);
 assert.throws(()=>mergeSnapshots([{messages:[u,a]},{messages:[a,u]}]),/conflicting/);
 assert.throws(()=>mergeSnapshots([{messages:[u,a]},{messages:[{...a,text:'changed'}]}]),/changed/);
});
test('lazy placeholder gains its image without persisting a false empty warning',()=>{
 const blank={...m('a'),text:''},full={...blank,media:[{id:'img',kind:'image',name:'Image',width:50,height:40}]};
 const merged=mergeSnapshots([{messages:[blank],issues:['empty_message:a']},{messages:[full]}]);
 assert.deepEqual(merged.mediaIds,['img']);assert.deepEqual(merged.issues,[]);
});
test('expired media refreshes and reacquires the same identity; wrong identity never downloads',async()=>{
 let refresh=0,downloads=0;
 const result=await recoverMedia([{id:'a:image:0'}],{
  refreshSource:async()=>refresh++,locate:async id=>({id,url:refresh?'fresh':'expired'}),
  download:async item=>{downloads++;if(item.url==='expired')throw Error('403 signed expiry');return 'image.png';},
  verify:async()=>({sha256:'verified'})
 });
 assert.equal(result[0].status,'ready');assert.equal(result[0].attempts,2);assert.equal(refresh,1);assert.equal(downloads,2);
 downloads=0;
 const wrong=await recoverMedia([{id:'a'}],{refreshSource:async()=>{},locate:async()=>({id:'other'}),download:async()=>downloads++,verify:async()=>true});
 assert.equal(wrong[0].status,'missing');assert.equal(wrong[0].attempts,3);assert.equal(downloads,0);
});
test('invalid downloads retry boundedly; permission failures stop without bypass',async()=>{
 let refresh=0;
 const invalid=await recoverMedia([{id:'a'}],{refreshSource:async()=>refresh++,locate:async id=>({id}),download:async()=> 'error.xml',verify:async()=>false});
 assert.equal(invalid[0].status,'missing');assert.equal(refresh,2);
 const denied=await recoverMedia([{id:'a'}],{locate:async()=>{throw Object.assign(Error('private'),{code:'ACCESS_DENIED'});}});
 assert.equal(denied[0].attempts,1);assert.equal(denied[0].reason,'access_denied');
 assert.ok(!JSON.stringify(denied).includes('private'));
});
test('DOM capture scopes text to messages, retains raw user text and deduplicates widget labels',()=>{
 const dom=new JSDOM(`<div>Unrelated sidebar</div><div data-chatgpt-search-message-ids="u"><h4 data-conversation-role="user"></h4><div data-user-message-bubble><div class="whitespace-pre-wrap"># Original\n\n<code>#071633</code>\nLast line</div><button>Show more</button></div></div><div data-chatgpt-search-message-ids="a"><h4 data-conversation-role="assistant"></h4><div data-markdown-text-style="assistant-message">Response\nClosing<label>Closing<input type="radio"></label></div><img alt="Image" src="https://example.invalid/image"></div>`,{runScripts:'outside-only'});
 // jsdom has no layout/innerText; use textContent only for this DOM unit test.
 Object.defineProperty(dom.window.HTMLElement.prototype,'innerText',{get(){return this.textContent;}});
 const result=dom.window.eval('('+captureSnapshot.toString()+')()');
 assert.equal(result.messages.length,2);assert.equal(result.messages[0].text,'# Original\n\n`#071633`\nLast line');
 assert.equal(result.messages[1].media.length,1);assert.ok(!JSON.stringify(result).includes('Unrelated sidebar'));
 dom.window.close();
});
