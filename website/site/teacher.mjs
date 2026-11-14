import {element} from './learning.mjs';
import {renderClassroom,renderEvidence,groupStudents,refreshLabel} from './classroom-view.mjs';
import {mountReplay} from './replay.mjs';
const $=id=>document.getElementById(id);let key='',timer=null,inflight=false,lastRefresh=null,rows=[],filter=null,player=null,generation=0;
async function api(path){const response=await fetch('/api/practice/'+path,{credentials:'same-origin',headers:{'X-Practice-Owner':key},signal:AbortSignal.timeout(15000)});const body=await response.json();if(!response.ok){const e=Error(typeof body.detail==='string'?body.detail:'Classroom unavailable');e.status=response.status;throw e}return body}
function error(e){$('teacher-error').textContent=e.message;$('teacher-error').hidden=false}
function lock(){generation++;key='';rows=[];clearTimeout(timer);player?.destroy();$('teacher-students').replaceChildren();$('teacher-detail').replaceChildren();$('teacher-replay-panel').hidden=true;$('teacher-dashboard').hidden=true;$('teacher-login').hidden=false}
async function inspect(student){
 const gen=generation;try{const detail=await api(`classroom/${student.id}/detail`);if(gen!==generation)return;
  const root=$('teacher-detail');root.hidden=false;renderEvidence(root,student,detail,async actionId=>{
   try{const {events}=await api(`classroom/${student.id}/events`);if(gen!==generation)return;player?.destroy();const index=events.findIndex(e=>e.kind.endsWith('_finished')&&e.payload.action_id===actionId);$('teacher-replay-panel').hidden=false;player=mountReplay($('teacher-replay'),events,{startIndex:index<0?events.length-1:index});$('teacher-replay-panel').scrollIntoView?.({behavior:'smooth',block:'start'})}catch(e){error(e)}
  });root.scrollIntoView?.({behavior:'smooth',block:'start'});
 }catch(e){if(gen===generation)error(e)}
}
function draw(){
 renderClassroom($('teacher-students'),filter?rows.filter(s=>s.group_key===filter):rows,inspect);
 const groups=$('teacher-groups');groups.replaceChildren();const all=element(document,'button',`All students (${rows.length})`,'teacher-group');all.type='button';all.setAttribute('aria-pressed',String(!filter));all.addEventListener('click',()=>{filter=null;draw()});groups.append(all);
 for(const group of groupStudents(rows)){const b=element(document,'button',`${group.label} (${group.students.length})`,'teacher-group');b.type='button';b.setAttribute('aria-pressed',String(filter===group.key));b.addEventListener('click',()=>{filter=filter===group.key?null:group.key;draw()});groups.append(b)}
}
async function refresh(){
 clearTimeout(timer);if(inflight||!key||document.hidden)return;inflight=true;const gen=generation;$('teacher-refresh-button').disabled=true;
 try{const data=await api('classroom');if(gen!==generation)return;rows=data.sessions;lastRefresh=Date.now();$('teacher-error').hidden=true;$('teacher-login').hidden=true;$('teacher-dashboard').hidden=false;$('teacher-refresh').textContent=refreshLabel(lastRefresh);draw()}
 catch(e){if(gen!==generation)return;if(e.status===401){lock();error(e)}else{error(e);$('teacher-refresh').textContent=refreshLabel(lastRefresh,e.message)}}
 finally{inflight=false;$('teacher-refresh-button').disabled=false;if(key&&!document.hidden)timer=setTimeout(refresh,5000)}
}
$('teacher-login').addEventListener('submit',e=>{e.preventDefault();key=$('teacher-token').value;$('teacher-token').value='';generation++;refresh()});
$('teacher-refresh-button').addEventListener('click',refresh);$('teacher-logout').addEventListener('click',lock);
$('teacher-replay-close').addEventListener('click',()=>{player?.destroy();$('teacher-replay-panel').hidden=true});
document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(!document.hidden)refresh()});
