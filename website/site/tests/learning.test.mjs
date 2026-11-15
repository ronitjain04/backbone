import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {reduceEvents,momentLabel,outcomeLabel,memoryQuantities} from '../learning.mjs';
import {mountReplay} from '../replay.mjs';
const events=[
 {seq:1,kind:'check_requested',exercise_id:'mem-03',payload:{answer:'2',work:'2048 bits = 2048 bytes'}},
 {seq:2,kind:'check_finished',exercise_id:'mem-03',payload:{status:'incorrect',misconception:{evidence:'2048 bits = 2048 bytes',label:'Units'}}},
 {seq:3,kind:'hint_finished',exercise_id:'mem-03',payload:{status:'hint',level:1,message:'Count locations'}},
 {seq:4,kind:'visual_opened',exercise_id:'mem-03',payload:{stage:2,address_bits:2,bits_per_location:4}},
 {seq:5,kind:'outcome_recorded',exercise_id:'mem-03',payload:{outcome:'corrected_with_help'}},
 {seq:6,kind:'outcome_recorded',exercise_id:'mem-03-follow',payload:{outcome:'solved_independently'}}
].map((e,i)=>({...e,at:new Date(i*1000).toISOString()}));
test('replay reconstructs evidence, help, correction and independent transfer without future state',()=>{
 const before=reduceEvents(events,1);assert.equal(before.exercises['mem-03'].answer,'2');assert.equal(before.exercises['mem-03'].outcome,null);
 const end=reduceEvents(events,5);assert.equal(end.exercises['mem-03'].visual.stage,2);assert.equal(end.exercises['mem-03-follow'].outcome,'solved_independently');
 assert.equal(momentLabel(events[1]),'Supported mistake');assert.equal(momentLabel(events[4]),'Correction with help');assert.equal(momentLabel(events[5]),'Independent follow-up');
 assert.equal(outcomeLabel('historical_unclassified'),'Completed · historical outcome unclassified');
 assert.deepEqual(reduceEvents([],0).exercises,{});
});
test('bounded contrasting visual quantities remain exact',()=>{
 assert.deepEqual(memoryQuantities(2,4),{locations:4,totalBits:16,totalBytes:2});
 assert.throws(()=>memoryQuantities(100,4));assert.throws(()=>memoryQuantities(2,-1));
});
test('replay controls seek, pause and safely render hostile evidence',()=>{
 const dom=new JSDOM('<div id="root"></div>');const root=dom.window.document.getElementById('root');
 const hostile=[{...events[0],payload:{answer:'<img src=x onerror=alert(1)>',work:'<script>bad()</script>'}},events[1]];
 const player=mountReplay(root,hostile);
 assert.equal(root.querySelectorAll('script,img').length,0);assert.match(root.textContent,/<script>/);
 assert.ok(root.querySelector('[data-replay-play]'));const slider=root.querySelector('input[type=range]');slider.value='0';slider.dispatchEvent(new dom.window.Event('input'));
 assert.match(root.textContent,/1 \/ 2/);player.seek(1);assert.match(root.textContent,/2 \/ 2/);player.destroy();
});

test('memory help waits for a persisted response and restores actual recovered settings',async()=>{
 const {mountMemoryVisual}=await import('../memory-visual.mjs');
 const dom=new JSDOM('<div id="root"></div>'),root=dom.window.document.getElementById('root');let resolve;
 const visual=mountMemoryVisual(root,{exercise:{id:'mem-03'},request:()=>new Promise(r=>resolve=r)});
 root.querySelector('button').click();assert.equal(root.querySelector('.memory-grid'),null);
 resolve({status:'visual',stage:2,address_bits:3,bits_per_location:4,message:'Count locations',sources:[]});await new Promise(r=>setTimeout(r,0));
 assert.match(root.textContent,/3 address bits → 8 distinct locations/);
 assert.equal(root.querySelectorAll('.memory-row').length,8);visual.destroy();
});

test('legacy correct attempts retain conservative historical completion in replay',()=>{
 const old=[{kind:'check_finished',exercise_id:'num-01',payload:{status:'correct'}}];
 assert.equal(reduceEvents(old,0).exercises['num-01'].outcome,'historical_unclassified');
 old.push({kind:'outcome_recorded',exercise_id:'num-01',payload:{outcome:'solved_independently'}});
 assert.equal(reduceEvents(old,1).exercises['num-01'].outcome,'solved_independently');
});
