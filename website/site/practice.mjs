import {renderAnswer} from './answer-renderer.mjs';
const $=id=>document.getElementById(id);
let state=null,selected=null,timer=null,saving=Promise.resolve(),busy=false,events=[],ownerKey='';
const pendingActions=new Map();
const topics={numbers:'Number representation',memory:'Memory & addressing',lc3:'LC-3 execution'};
const node=(tag,text,className)=>{const el=document.createElement(tag);el.textContent=text;if(className)el.className=className;return el};
async function api(path,data,headers={}){
 const response=await fetch('/api/practice/'+path,{credentials:'same-origin',...(data===undefined?{}:{method:'POST',body:JSON.stringify(data)}),headers:{'Content-Type':'application/json',...headers},signal:AbortSignal.timeout(75000)});
 const body=await response.json();if(!response.ok){const err=Error(typeof body.detail==='string'?body.detail:'Practice is unavailable. Keep your work and retry.');err.status=response.status;throw err}return body;
}
function error(err){$('practice-error').textContent=err.message;$('practice-error').hidden=false}
function clearError(){$('practice-error').hidden=true}
function progress(){return state.progress[selected]??={answer:'',work:'',revision:0,completed:false,hint_level:0}}
function localKey(){return `backbone-practice:${state.session_id}:${selected}`}
function remember(){try{localStorage.setItem(localKey(),JSON.stringify({answer:$('practice-answer').value,work:$('practice-work').value,revision:progress().revision}))}catch{}}
function setBusy(value){busy=value;for(const id of ['practice-answer','practice-work','practice-check','practice-hint','practice-follow','practice-retry-save','practice-delete'])$(id).disabled=value;document.querySelectorAll('#exercise-list button').forEach(b=>b.disabled=value);$('practice-selector').disabled=value}
function list(){
 const target=$('exercise-list');target.replaceChildren();const picker=$('practice-selector');picker.replaceChildren();
 for(const [topic,title] of Object.entries(topics)){
  const group=node('div','', 'practice-topic');group.append(node('h3',title));const optionGroup=document.createElement('optgroup');optionGroup.label=title;
  state.exercises.filter(e=>e.topic===topic&&!e.id.endsWith('-follow')).forEach(e=>{
   const completed=state.progress[e.id]?.completed;const option=node('option',`${completed?'✓ ':''}${e.title}`);option.value=e.id;option.selected=e.id===selected;optionGroup.append(option);const b=node('button',`${completed?'✓ ':''}${e.title}`);
   b.type='button';b.dataset.exercise=e.id;b.setAttribute('aria-current',String(e.id===selected));b.addEventListener('click',async()=>{if(busy)return;setBusy(true);try{await flush();await api('select',{exercise_id:e.id});select(e.id)}catch(err){error(err)}finally{setBusy(false)}});group.append(b);
  });target.append(group);picker.append(optionGroup);
 }
 const completed=state.exercises.filter(e=>!e.id.endsWith('-follow')&&state.progress[e.id]?.completed).length;
 $('practice-progress').textContent=`${completed} / 18 completed · CS 2110`;
}
function sources(container,refs){
 for(const r of refs??[]){const d=node('div','', 'source');d.append(node('b',`${r.source} · ${r.details}`));if(r.text)d.append(node('p',r.text));container.append(d)}
}
function feedback(result){
 const target=$('practice-feedback');target.replaceChildren();
 const labels={correct:'Correct',incorrect:'Let’s revisit one step',needs_clarification:'Help me understand your work',unavailable:'Your work is saved',hint:`Hint ${result.level??''} of 3`};
 target.append(node('div',labels[result.status]??'Tutor feedback','practice-feedback-label'),renderAnswer(result.message??''));
 if(result.clarification)target.append(node('p',result.clarification));
 if(result.misconception){target.append(node('h3',result.misconception.label),node('blockquote',result.misconception.evidence));}
 if(result.sources?.length){const d=node('details','');d.append(node('summary','Check the supporting sources'));sources(d,result.sources);target.append(d)}
 if(result.criteria?.length){const d=node('details','');d.append(node('summary','How this was assessed'));for(const c of result.criteria)d.append(node('p',`${c.description??c.id}: ${c.status}${c.evidence?' — “'+c.evidence+'”':''}`));target.append(d)}
}
function select(id){
 selected=id;const e=state.exercises.find(e=>e.id===id);const p=progress();
 $('exercise-topic').textContent=topics[e.topic]+(id.endsWith('-follow')?' · Follow-up':'');$('exercise-title').textContent=e.title;
 $('exercise-prompt').replaceChildren(renderAnswer(e.prompt));$('exercise-input-help').textContent=e.input_help;
 $('exercise-references').replaceChildren();sources($('exercise-references'),e.references);
 let draft=p;try{const local=JSON.parse(localStorage.getItem(localKey()));if(local&&local.revision===p.revision)draft=local}catch{}
 $('practice-answer').value=draft.answer;$('practice-work').value=draft.work;
 $('practice-save').textContent=draft===p?'Saved':'Recovered draft · saving…';
 $('practice-feedback').replaceChildren(node('p','Your first attempt is a starting point. What do you think?'));
 const last=state.actions.filter(a=>a.exercise_id===id&&a.result).at(-1);if(last)feedback(last.result);
 $('practice-follow').hidden=!p.completed||id.endsWith('-follow');list();
 if(draft!==p)timer=setTimeout(()=>flush().catch(error),600);
}
function show(s){state=s;$('practice-entry').hidden=true;$('practice-workspace').hidden=false;$('practice-replay').hidden=false;select(selected&&s.exercises.some(e=>e.id===selected)?selected:(s.selected_exercise??'num-01'))}
async function saveCurrent(){
 if(!state||!selected)return;
 const id=selected,p=progress(),answer=$('practice-answer').value,work=$('practice-work').value,key=localKey();
 if(answer===p.answer&&work===p.work){$('practice-save').textContent='Saved';return}
 $('practice-save').textContent='Saving…';
 try{
  const saved=await api('draft',{exercise_id:id,answer,work,revision:p.revision});
  Object.assign(p,{answer,work,revision:saved.revision});
  // An edit made during the request must remain recoverable until the next save.
  if(selected===id&&$('practice-answer').value===answer&&$('practice-work').value===work){try{localStorage.removeItem(key)}catch{}}else if(selected===id)remember();
  $('practice-save').textContent='Saved';
 }catch(err){$('practice-save').textContent='Not saved · retry';throw err}
}
function flush(){clearTimeout(timer);saving=saving.catch(()=>{}).then(saveCurrent);return saving}
for(const id of ['practice-answer','practice-work'])$(id).addEventListener('input',()=>{remember();$('practice-save').textContent='Unsaved changes';clearTimeout(timer);timer=setTimeout(()=>flush().catch(error),600)});
$('practice-selector').addEventListener('change',async()=>{const id=$('practice-selector').value;if(busy)return;setBusy(true);try{await flush();await api('select',{exercise_id:id});select(id)}catch(err){error(err);$('practice-selector').value=selected}finally{setBusy(false)}});
$('practice-start').addEventListener('click',async()=>{clearError();$('practice-start').disabled=true;try{show(await api('start',{name:$('practice-name').value}))}catch(err){error(err)}finally{$('practice-start').disabled=false}});
async function action(kind){
 if(busy)return;setBusy(true);clearError();
 try{
  await flush();const p=progress();
  const pendingKey=`backbone-practice-action:${state.session_id}:${selected}:${kind}`;
  let request=pendingActions.get(pendingKey);
  if(!request){try{request=JSON.parse(localStorage.getItem(pendingKey))}catch{}}
  if(!request){request={exercise_id:selected,answer:p.answer,work:p.work,revision:p.revision,request_key:crypto.randomUUID()};pendingActions.set(pendingKey,request);try{localStorage.setItem(pendingKey,JSON.stringify(request))}catch{}}
  const recovered=request.answer!==p.answer||request.work!==p.work;
  const result=await api(kind,request);
  pendingActions.delete(pendingKey);try{localStorage.removeItem(pendingKey)}catch{}
  feedback(result);state.actions.push({exercise_id:selected,kind,result});
  if(recovered)$('practice-feedback').append(node('p','Recovered feedback for your earlier attempt. Your current draft is still here; check it when you are ready.','practice-note'));
  if(result.status==='correct')p.completed=true;if(result.status==='hint')p.hint_level=result.level;
  $('practice-follow').hidden=!p.completed||selected.endsWith('-follow');list();
 }catch(err){error(err)}finally{setBusy(false)}
}
$('practice-form').addEventListener('submit',e=>{e.preventDefault();action('check')});$('practice-hint').addEventListener('click',()=>action('hint'));
$('practice-retry-save').addEventListener('click',()=>{clearError();flush().catch(error)});
$('practice-follow').addEventListener('click',async()=>{try{await flush();const id=selected+'-follow';await api('select',{exercise_id:id});select(id)}catch(err){error(err)}});
$('practice-delete').addEventListener('click',async()=>{
 if(!confirm('Delete your saved demo work, hints, and replay history?'))return;
 try{await saving.catch(()=>{});clearTimeout(timer);await api('delete',{});const prefix=`backbone-practice:${state.session_id}:`,pendingPrefix=`backbone-practice-action:${state.session_id}:`;try{Object.keys(localStorage).filter(k=>k.startsWith(prefix)||k.startsWith(pendingPrefix)).forEach(k=>localStorage.removeItem(k))}catch{}state=null;selected=null;$('practice-workspace').hidden=true;$('practice-replay').hidden=true;$('practice-replay-panel').hidden=true;$('practice-entry').hidden=false}catch(err){error(err)}
});
function replay(){
 const i=Number($('replay-step').value),event=events[i];if(!event)return;
 $('replay-position').textContent=`${i+1} / ${events.length} · ${new Date(event.at).toLocaleString()} · ${event.kind.replaceAll('_',' ')}`;
 const target=$('replay-event');target.replaceChildren(node('h3',event.exercise_id??'Session started'));
 // Render the accumulated state at this point, rather than regenerating tutor responses.
 let answer='',work='',results=[];
 for(const prior of events.slice(0,i+1)){
  if(prior.exercise_id!==event.exercise_id)continue;
  if('answer' in prior.payload){answer=prior.payload.answer;work=prior.payload.work??''}
  if(prior.kind.endsWith('_finished'))results.push(prior.payload);
 }
 target.append(node('h4','Submitted work'),node('pre',answer),node('pre',work));
 for(const r of results){target.append(node('h4',r.status),node('p',r.message??''));if(r.misconception)target.append(node('blockquote',r.misconception.evidence));if(r.sources?.length){const details=node('details','');details.append(node('summary','Supporting sources for this step'));sources(details,r.sources);target.append(details)}}
}
function showReplay(items){events=items;$('practice-replay-panel').hidden=false;$('replay-step').max=String(Math.max(0,events.length-1));$('replay-step').value=String(Math.max(0,events.length-1));replay();const panel=$('practice-replay-panel');panel.tabIndex=-1;panel.focus({preventScroll:true});panel.scrollIntoView?.({behavior:'smooth',block:'start'})}
$('practice-replay').addEventListener('click',async()=>{try{await flush();showReplay((await api('events')).events)}catch(err){error(err)}});
$('replay-step').addEventListener('input',replay);$('replay-close').addEventListener('click',()=>{$('practice-replay-panel').hidden=true});
$('practice-owner-load').addEventListener('click',async()=>{
 ownerKey=$('practice-owner-key').value;$('practice-owner-key').value='';
 try{const data=await api('classroom',undefined,{'X-Practice-Owner':ownerKey});const target=$('practice-classroom');target.replaceChildren();
  for(const s of data.sessions){const b=node('button',`${s.display_name} · ${s.completed} completed · ${new Date(s.created_at).toLocaleString()}`,'clear-button');b.addEventListener('click',async()=>{try{showReplay((await api(`classroom/${s.id}/events`,undefined,{'X-Practice-Owner':ownerKey})).events)}catch(err){error(err)}});target.append(b)}
 }catch(err){ownerKey='';error(err)}
});
api('state').then(show).catch(err=>{if(err.status===401)$('practice-entry').hidden=false;else error(err)});
