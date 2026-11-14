import {memoryQuantities,element,sourceDetails} from './learning.mjs';
export function mountMemoryVisual(root,{exercise,progress={},request,onState=()=>{}}){
 const doc=root.ownerDocument,n=(...a)=>element(doc,...a);root.replaceChildren();
 if(!/^mem-(03|06)(-follow)?$/.test(exercise.id))return {destroy(){}};
 let settings={stage:progress.stage??1,address_bits:progress.address_bits??2,bits_per_location:progress.bits_per_location??4},busy=false,alive=true;
 const open=n('button',progress.stage?'Resume memory explanation':'Explore a memory diagram','button secondary'),panel=n('div','','memory-panel'),status=n('p','','practice-note');open.type='button';root.append(open,status,panel);
 async function update(next){if(busy)return;busy=true;open.disabled=true;panel.querySelectorAll('button,input').forEach(x=>x.disabled=true);status.textContent='Saving your explanation step…';
  try{const r=await request(next);if(!alive)return;if(r.status!=='visual')throw Error(r.message);settings={stage:r.stage,address_bits:r.address_bits,bits_per_location:r.bits_per_location};onState(r);status.textContent='Explanation saved · counts as help for this exercise';render(r);open.hidden=true}catch(err){if(alive)status.textContent=err.message}finally{busy=false;open.disabled=false;panel.querySelectorAll('button,input').forEach(x=>x.disabled=false)}}
 function render(r){
  panel.replaceChildren(n('div',`MEMORY LAB · STEP ${r.stage} OF 3`,'section-label'),n('h3','Locations and what fits inside them'),n('p',r.example_note));
  if(r.evidence)panel.append(n('p','Relevant supported step from your work:'),n('blockquote',r.evidence.evidence,'evidence-quote'),n('p',`Suspected: ${r.evidence.label}. Compare the quantities below with this step.`));
  if(r.clarification)panel.append(n('p',r.clarification));panel.append(n('p',r.message));
  const fields=n('div','','memory-controls');for(const [key,label,min,max] of [['address_bits','Address bits → number of locations',1,8],['bits_per_location','Bits per location → addressability',1,32]]){const l=n('label',label),input=doc.createElement('input');input.type='number';input.min=min;input.max=max;input.value=settings[key];input.setAttribute('aria-label',label);input.addEventListener('change',()=>{const v=Number(input.value);if(!Number.isInteger(v)||v<min||v>max){input.value=settings[key];return}update({...settings,[key]:v})});l.append(input);fields.append(l)}panel.append(fields);
  const q=memoryQuantities(settings.address_bits,settings.bits_per_location),grid=n('div','','memory-grid');grid.setAttribute('aria-label',`${q.locations} locations, each with ${settings.bits_per_location} bits`);
  for(let i=0;i<Math.min(q.locations,8);i++){const row=n('div','','memory-row');row.append(n('code',i.toString(2).padStart(settings.address_bits,'0')));const cells=n('div','','memory-cells');for(let j=0;j<Math.min(settings.bits_per_location,16);j++)cells.append(n('span','·'));if(settings.bits_per_location>16)cells.append(n('span','…'));row.append(cells,n('small',`${settings.bits_per_location} bits`));grid.append(row)}if(q.locations>8)grid.append(n('p',`… ${q.locations-8} more locations`));panel.append(grid,n('p',`${settings.address_bits} address bits → ${q.locations} distinct locations`,'memory-equation'));
  if(r.stage>=2)panel.append(n('p',`${q.locations} locations × ${settings.bits_per_location} bits per location = ${q.totalBits} total bits`,'memory-equation'));
  if(r.stage>=3)panel.append(n('p',`${q.totalBits} bits ÷ 8 = ${q.totalBytes} bytes. Now apply the relationship to your own values.`,'memory-equation'));
  const controls=n('div','','practice-actions');if(r.stage>1){const b=n('button','Previous step','clear-button');b.type='button';b.addEventListener('click',()=>update({...settings,stage:r.stage-1}));controls.append(b)}if(r.stage<3){const b=n('button','Show the next relationship','button secondary');b.type='button';b.addEventListener('click',()=>update({...settings,stage:r.stage+1}));controls.append(b)}panel.append(controls,sourceDetails(doc,r.sources));
 }
 open.addEventListener('click',()=>update(settings));return {destroy(){alive=false;root.replaceChildren()}};
}
