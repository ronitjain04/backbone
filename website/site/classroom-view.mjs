import {element,outcomeLabel,sourceDetails} from './learning.mjs';
export const signalLabel=value=>({active:'Active signal',stale:'Stale signal',disconnected:'Disconnected or closed'}[value]??'No signal yet');
export function refreshLabel(at,error){return error?`${error} · Showing the last successful refresh${at?' at '+new Date(at).toLocaleTimeString():': none yet'}.`:`Updated ${new Date(at).toLocaleTimeString()} · refreshes every 5 seconds`;}
export function groupStudents(rows){const groups=new Map();for(const s of rows){if(!s.group_key)continue;const g=groups.get(s.group_key)??{key:s.group_key,label:s.group_key==='clarification'?'Clarification needed':`${s.exercise_title??s.topic} · supported reasoning to revisit`,students:[]};g.students.push(s);groups.set(g.key,g)}return [...groups.values()]}
export function renderClassroom(root,rows,onInspect){
 const doc=root.ownerDocument,n=(...a)=>element(doc,...a);root.replaceChildren();if(!rows.length){root.append(n('p','No student sessions yet. Open practice in another browser to try the classroom.'));return}
 const table=n('table','','classroom-table'),caption=n('caption','Current activity and evidence · presence is inferred from browser signals'),head=n('thead'),hr=n('tr');
 for(const title of ['Student / exercise','Recent activity','Help / outcomes','Connection','Evidence'])hr.append(n('th',title));head.append(hr);const body=n('tbody');
 for(const s of rows){const row=n('tr'),identity=n('td'),activity=n('td'),outcomes=n('td'),signal=n('td'),inspect=n('td');
  identity.append(n('strong',s.display_name),n('small',s.id.slice(0,8)),n('p',s.exercise_title??s.current_exercise));
  activity.append(n('p',s.last_activity?new Date(s.last_activity).toLocaleTimeString():'No work yet'),n('small',s.diagnosis?'Suspected: '+s.diagnosis.label:s.clarification_needed?'Clarification needed':'No supported diagnosis'));
  outcomes.append(n('p',`${s.hints_used} hints delivered`),n('small','Original: '+outcomeLabel(s.parent_outcome)),n('small','Follow-up: '+outcomeLabel(s.follow_up_outcome)));
  signal.append(n('span',signalLabel(s.presence),'presence-badge '+s.presence));
  const b=n('button','Inspect work','clear-button');b.type='button';b.dataset.inspect='';b.addEventListener('click',()=>onInspect(s));inspect.append(b);row.append(identity,activity,outcomes,signal,inspect);body.append(row);
 }table.append(caption,head,body);root.append(table);
}
export function renderEvidence(root,student,detail,onReplay){
 const doc=root.ownerDocument,n=(...a)=>element(doc,...a);root.replaceChildren(n('h2',student.display_name+' · evidence'),n('p','Diagnoses are hypotheses supported by quoted work. Check the source and context before intervening.','practice-note'));
 if(!detail.attempts.length){root.append(n('p','No completed checks or hints yet.'));return}
 const selected=detail.attempts.filter(a=>a.exercise_id===student.current_exercise).slice(-12);
 for(const a of selected){const r=a.result??{},card=n('article','','teacher-attempt');card.append(n('h3',`${a.exercise_id} · ${a.kind} · ${r.status}`),n('small',new Date(a.created_at).toLocaleString()),n('h4','Submitted work'),n('pre',a.input.answer??''),n('pre',a.input.work??''),n('p',r.message??''));
  if(r.misconception)card.append(n('h4','Suspected: '+r.misconception.label),n('blockquote',r.misconception.evidence,'evidence-quote'));
  if(r.clarification)card.append(n('p',r.clarification));if(r.sources?.length)card.append(sourceDetails(doc,r.sources));
  const replay=n('button','Replay this moment','clear-button');replay.type='button';replay.addEventListener('click',()=>onReplay(a.id));card.append(replay);root.append(card);
 }if(!selected.length)root.append(n('p','No completed attempts on the currently selected exercise.'));
}
