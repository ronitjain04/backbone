export const outcomeLabel=value=>({solved_independently:'Solved independently',corrected_with_help:'Corrected with help',historical_unclassified:'Completed · historical outcome unclassified',pending_assistance:'Correct · waiting for an earlier help request'}[value]??'In progress');
export function memoryQuantities(addressBits,bitsPerLocation){
 if(!Number.isInteger(addressBits)||addressBits<1||addressBits>8||!Number.isInteger(bitsPerLocation)||bitsPerLocation<1||bitsPerLocation>32)throw Error('Visual values out of bounds');
 const locations=2**addressBits,totalBits=locations*bitsPerLocation;return {locations,totalBits,totalBytes:totalBits/8};
}
export function momentLabel(event){
 const p=event.payload??{};
 if(event.kind==='outcome_recorded')return p.outcome==='corrected_with_help'?'Correction with help':p.outcome==='solved_independently'?(event.exercise_id?.endsWith('-follow')?'Independent follow-up':'Independent solution'):'Completion';
 if(event.kind==='check_finished')return p.misconception?'Supported mistake':p.status==='correct'?'Correct attempt':p.status==='incorrect'?'Incorrect attempt':'Clarification / unavailable';
 if(event.kind==='hint_finished'&&p.status==='hint')return 'Hint';
 if(event.kind.startsWith('visual_'))return 'Interactive explanation';
 return event.kind.replaceAll('_',' ');
}
export function reduceEvents(events,index){
 const state={exercises:{},selected:null};
 for(const e of events.slice(0,index+1)){
  if(!e.exercise_id)continue;state.selected=e.exercise_id;
  const p=e.payload??{},x=state.exercises[e.exercise_id]??={answer:'',work:'',results:[],hints:[],outcome:null,visual:null};
  if('answer' in p){x.answer=p.answer;x.work=p.work??''}
  if(e.kind==='check_finished')x.results.push(p);
  if(e.kind==='hint_finished'&&p.status==='hint')x.hints.push(p);
  if(e.kind.startsWith('visual_'))x.visual=p;
  if(p.outcome)x.outcome=p.outcome;
 }
 return state;
}
export function element(doc,tag,text='',className=''){const el=doc.createElement(tag);el.textContent=text;if(className)el.className=className;return el}
export function sourceDetails(doc,sources){
 const d=element(doc,'details'),summary=element(doc,'summary','Supporting sources');d.append(summary);
 for(const r of sources??[]){d.append(element(doc,'strong',`${r.source} · ${r.details??''}`));if(r.text)d.append(element(doc,'p',r.text))}return d;
}
