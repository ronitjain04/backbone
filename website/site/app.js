import {renderAnswer} from './answer-renderer.mjs';

const form=document.querySelector('#question-form'),input=document.querySelector('#question'),messages=document.querySelector('#messages'),send=document.querySelector('#send'),error=document.querySelector('#error'),welcome=document.querySelector('#welcome'),clear=document.querySelector('#clear');
const tabs=[...document.querySelectorAll('[data-course]')];
const suggestions=[...document.querySelectorAll('[data-question]')];
const courses={
 cs2110:{name:'CS 2110',title:'Computer organization & programming',subtitle:'CS 2110 · Fall 2026',source:'Textbook & lab material',description:'From transistors and binary to the LC-3 and C. Explanations use the selected course’s available material.',topics:['Digital logic','LC-3','C programming'],questions:['Why can the bus only hold one value?','What is the addressability of memory?','What is the purpose of using typedef before instantiating a struct?']},
 cs2200:{name:'CS 2200',title:'Computer systems & networks',subtitle:'CS 2200 topics · demo collection',source:'Original demo notes',description:'A small set of original notes on pipelining, caches, and virtual memory. These are illustrative study notes, not official course materials.',topics:['Pipelining','Memory','Caches'],questions:['Why do data hazards happen in a pipeline?','How are a cache and virtual memory different?','When does forwarding fail to resolve a hazard?']}
};
const states=Object.fromEntries(Object.keys(courses).map(id=>[id,{nodes:[],draft:'',error:'',busy:false,ready:null}]));
let selected='cs2200';
function count(){document.querySelector('#count').textContent=`${input.value.length} / 2000`}
function showStatus(){
 const state=states[selected],el=document.querySelector('#status');
 el.replaceChildren();const dot=document.createElement('span');dot.className='dot';
 const text=state.ready===null?`Checking ${courses[selected].name}…`:state.ready?`${courses[selected].name} · Live service configured`:`${courses[selected].name} · Not connected yet`;
 el.append(dot,document.createTextNode(text));el.classList.toggle('online',state.ready===true);
}
function renderChat(){
 const state=states[selected];
 messages.replaceChildren(welcome,...state.nodes);welcome.hidden=state.nodes.length>0;
 messages.setAttribute('aria-busy',String(state.busy));
 input.value=state.draft;input.readOnly=state.busy;send.disabled=state.busy;clear.disabled=state.busy;
 error.textContent=state.error;error.hidden=!state.error;count();showStatus();
 messages.scrollTop=messages.scrollHeight;
}
async function status(course){
 try{const r=await fetch('/api/status?course='+course);const d=await r.json();states[course].ready=d.ready===true}catch{states[course].ready=false}
 if(selected===course)showStatus();
}
function selectCourse(course){
 if(course===selected)return;
 states[selected].draft=input.value;
 selected=course;const info=courses[course];
 tabs.forEach(tab=>{const active=tab.dataset.course===course;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1});
 document.querySelector('#course-workspace').setAttribute('aria-labelledby','tab-'+course);
 document.querySelector('#course-title').textContent=info.title;
 document.querySelector('#course-subtitle').textContent=info.subtitle;
 document.querySelector('#course-source').textContent=info.source;
 document.querySelector('#course-description').textContent=info.description;
 document.querySelector('#question-label').textContent=`Your ${info.name} question`;
 document.querySelector('#welcome-description').textContent=`Ask a question about ${info.name}. We’ll look for context in this course’s material, then build an explanation.`;
 const topics=document.querySelector('#welcome-topics');topics.replaceChildren();
 info.topics.forEach(topic=>{const span=document.createElement('span');span.textContent=topic;topics.append(span)});
 suggestions.forEach((button,i)=>{button.dataset.question=info.questions[i];const arrow=document.createElement('span');arrow.textContent='↗';button.replaceChildren(document.createTextNode(info.questions[i]),arrow)});
 input.placeholder=info.questions[0];
 renderChat();status(course);
}
function message(state,role,text,formatted=false){
 const article=document.createElement('article');article.className='message '+role;
 const label=document.createElement('div');label.className='message-label';label.textContent=role==='user'?'YOU':'BACKBONE';
 const body=formatted?renderAnswer(text):document.createElement('p');
 if(!formatted)body.textContent=text;
 article.append(label,body);state.nodes.push(article);return article;
}
input.addEventListener('input',()=>{states[selected].draft=input.value;count()});
input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey&&!e.isComposing){e.preventDefault();form.requestSubmit()}});
suggestions.forEach(button=>button.addEventListener('click',()=>{if(states[selected].busy)return;input.value=button.dataset.question;states[selected].draft=input.value;count();input.focus()}));
tabs.forEach((tab,index)=>{
 tab.addEventListener('click',()=>selectCourse(tab.dataset.course));
 tab.addEventListener('keydown',e=>{
  let next=index;
  if(e.key==='ArrowRight')next=(index+1)%tabs.length;
  else if(e.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;
  else if(e.key==='Home')next=0;
  else if(e.key==='End')next=tabs.length-1;
  else return;
  e.preventDefault();selectCourse(tabs[next].dataset.course);tabs[next].focus();
 });
});
clear.addEventListener('click',()=>{const state=states[selected];if(state.busy)return;state.nodes=[];state.draft='';state.error='';renderChat();input.focus()});
form.addEventListener('submit',async e=>{
 e.preventDefault();const course=selected,state=states[course],query=input.value.trim();if(state.busy||!query)return;
 state.draft=input.value;state.busy=true;state.error='';
 const user=message(state,'user',query),loading=message(state,'assistant','Finding relevant notes and building an explanation…');loading.classList.add('loading');renderChat();
 try{
  const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,course}),signal:AbortSignal.timeout(75000)});
  const data=await r.json();
  if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'The answer service is unavailable. Please try again.');
  if(typeof data.answer!=='string')throw Error('The service returned an invalid answer. Please try again.');
  state.nodes=state.nodes.filter(node=>node!==loading);const answer=message(state,'assistant',data.answer,true);
  if(data.citations?.length){
   const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent=`Explore ${data.citations.length} retrieved source${data.citations.length===1?'':'s'}`;details.append(summary);
   data.citations.forEach((citation,i)=>{const source=document.createElement('div');source.className='source';const title=document.createElement('b');title.textContent=`[${i+1}] ${citation.source}${citation.details?' · '+citation.details:''}`;source.append(title);const text=document.createElement('p');text.textContent=data.context?.[i]?.text||'No excerpt available.';source.append(text);details.append(source)});answer.append(details);
  }
  state.draft='';
 }catch(err){
  state.nodes=state.nodes.filter(node=>node!==loading&&node!==user);
  state.error=err.name==='TimeoutError'?'The model took too long. Your question is saved; try again.':err.message||'Connection failed. Your question is saved; try again.';
 }finally{state.busy=false;if(selected===course){renderChat();input.focus()}}
});
status(selected);
