import {reduceEvents,momentLabel,outcomeLabel,element,sourceDetails,memoryQuantities} from './learning.mjs';
export function mountReplay(root,events,{startIndex=events.length-1}={}){
 const doc=root.ownerDocument,n=(...a)=>element(doc,...a);let index=Math.max(0,startIndex),timer=null,playing=false;
 root.replaceChildren();const controls=n('div','','replay-controls'),play=n('button','Play'),prev=n('button','Previous moment'),next=n('button','Next moment'),speed=doc.createElement('select');
 play.type=prev.type=next.type='button';play.dataset.replayPlay='';speed.setAttribute('aria-label','Replay speed');
 for(const v of [0.5,1,2]){const o=n('option',`${v}×`);o.value=v;o.selected=v===1;speed.append(o)}
 const slider=doc.createElement('input');slider.type='range';slider.min=0;slider.max=Math.max(0,events.length-1);slider.setAttribute('aria-label','Replay timeline');slider.id='replay-step';
 const position=n('p'),content=n('div');content.id='replay-event';position.id='replay-position';position.setAttribute('aria-live','polite');
 controls.append(prev,play,next,speed);root.append(controls,slider,position,n('p','Playback compresses idle gaps longer than 3 seconds. Event timestamps show the original timing.','practice-note'),content);
 const pause=()=>{playing=false;clearTimeout(timer);play.textContent='Play'};
 function render(){
  slider.value=index;const e=events[index];content.replaceChildren();if(!e){position.textContent='No recorded events yet.';play.disabled=true;return}
  position.textContent=`${index+1} / ${events.length} · ${new Date(e.at).toLocaleString()} · ${momentLabel(e)}`;
  const state=reduceEvents(events,index),id=state.selected,x=state.exercises[id];
  content.append(n('div',momentLabel(e),'replay-milestone'),n('h3',id??'Session'));
  if(!x)return;content.append(n('h4','Attempted work'),n('pre',x.answer),n('pre',x.work));
  for(const r of x.results){content.append(n('h4',r.status),n('p',r.message??''));if(r.misconception){content.append(n('p','Suspected: '+r.misconception.label),n('blockquote',r.misconception.evidence,'evidence-quote'))}if(r.clarification)content.append(n('p',r.clarification));if(r.sources?.length)content.append(sourceDetails(doc,r.sources))}
  for(const r of x.hints){content.append(n('h4',`Hint ${r.level}`),n('p',r.message??''));if(r.sources?.length)content.append(sourceDetails(doc,r.sources))}
  if(x.visual){const v=x.visual;content.append(n('h4',`Visual · step ${v.stage}`),n('p',v.message??''));try{const q=memoryQuantities(v.address_bits,v.bits_per_location);content.append(n('p',`${q.locations} locations × ${v.bits_per_location} bits per location = ${q.totalBits} bits (${q.totalBytes} bytes)`))}catch{} }
  if(x.outcome)content.append(n('p',outcomeLabel(x.outcome),'learning-outcome'));
 }
 function seek(i){pause();index=Math.max(0,Math.min(events.length-1,i));render()}
 function schedule(){if(index>=events.length-1){pause();return}const gap=Math.max(250,Math.min(3000,Date.parse(events[index+1].at)-Date.parse(events[index].at)||500));timer=setTimeout(()=>{index++;render();schedule()},gap/Number(speed.value))}
 play.addEventListener('click',()=>{if(playing){pause();return}if(index>=events.length-1)index=0;playing=true;play.textContent='Pause';render();schedule()});
 slider.addEventListener('input',()=>seek(Number(slider.value)));speed.addEventListener('change',()=>{if(playing){clearTimeout(timer);schedule()}});
 const significant=e=>['check_finished','outcome_recorded','visual_opened','visual_changed','hint_finished'].includes(e.kind);
 prev.addEventListener('click',()=>{for(let i=index-1;i>=0;i--)if(significant(events[i])){seek(i);return}seek(0)});
 next.addEventListener('click',()=>{for(let i=index+1;i<events.length;i++)if(significant(events[i])){seek(i);return}seek(events.length-1)});
 render();return {seek,destroy(){pause();root.replaceChildren()}};
}
