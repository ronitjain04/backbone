import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {groupStudents,signalLabel,refreshLabel,renderClassroom,renderEvidence} from '../classroom-view.mjs';
const rows=[{id:'1',display_name:'<img src=x>',current_exercise:'mem-03',exercise_title:'Capacity',topic:'memory',presence:'stale',group_key:'memory:concept',diagnosis:{label:'Units',evidence:'<script>wrong</script>'},hints_used:2,parent_outcome:'corrected_with_help'},{id:'2',display_name:'B',group_key:'clarification',clarification_needed:true,presence:'disconnected',hints_used:0}];
test('groups only share explicit evidence concept keys and uncertainty stays separate',()=>{
 assert.equal(groupStudents(rows)[0].key,'memory:concept');assert.equal(groupStudents(rows)[1].key,'clarification');
 assert.equal(signalLabel('stale'),'Stale signal');assert.equal(signalLabel('disconnected'),'Disconnected or closed');
 assert.match(refreshLabel(null,'Offline'),/Offline.*last successful refresh/i);
});
test('teacher rows and evidence render hostile input literally and offer inspection',()=>{
 const dom=new JSDOM('<div id="list"></div><div id="detail"></div>'),doc=dom.window.document;let selected;
 renderClassroom(doc.getElementById('list'),rows,s=>selected=s);
 assert.equal(doc.querySelectorAll('img,script').length,0);assert.match(doc.body.textContent,/<img src=x>/);
 doc.querySelector('button[data-inspect]').click();assert.equal(selected.id,'1');
 renderEvidence(doc.getElementById('detail'),rows[0],{attempts:[{id:'a',exercise_id:'mem-03',kind:'check',created_at:new Date().toISOString(),input:{answer:'2',work:'<script>wrong</script>'},result:{status:'incorrect',misconception:rows[0].diagnosis,sources:[]}}]},()=>{});
 assert.equal(doc.querySelectorAll('script').length,0);assert.match(doc.getElementById('detail').textContent,/Suspected/);
});

test('teacher refresh preserves last good data on failure and locks private data away',async()=>{
 const {readFile}=await import('node:fs/promises'),{build}=await import('esbuild');
 const html=await readFile(new URL('../teacher.html',import.meta.url),'utf8');
 const bundle=await build({entryPoints:[new URL('../teacher.mjs',import.meta.url).pathname],bundle:true,write:false,format:'iife',platform:'browser'});
 const dom=new JSDOM(html,{url:'https://demo.test/teacher.html',runScripts:'outside-only',pretendToBeVisual:true});let fail=false;
 dom.window.fetch=async()=>({ok:!fail,status:fail?503:200,json:async()=>fail?{detail:'Offline'}:{sessions:rows}});
 dom.window.eval(bundle.outputFiles[0].text);const doc=dom.window.document,tick=()=>new Promise(r=>setTimeout(r,15));
 try{doc.getElementById('teacher-token').value='secret';doc.getElementById('teacher-login').dispatchEvent(new dom.window.Event('submit',{cancelable:true}));await tick();
 assert.equal(doc.getElementById('teacher-dashboard').hidden,false);assert.equal(doc.getElementById('teacher-token').value,'');
 fail=true;doc.getElementById('teacher-refresh-button').click();await tick();assert.match(doc.getElementById('teacher-refresh').textContent,/last successful refresh/);assert.match(doc.getElementById('teacher-students').textContent,/<img/);
 doc.getElementById('teacher-logout').click();assert.equal(doc.getElementById('teacher-dashboard').hidden,true);assert.equal(doc.getElementById('teacher-students').textContent,'');
 }finally{dom.window.close()}
});
