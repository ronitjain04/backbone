import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';
const html=await readFile(new URL('../practice.html',import.meta.url),'utf8');
const tick=()=>new Promise(r=>setTimeout(r,15));
const bundle=build({entryPoints:[new URL('../practice.mjs',import.meta.url).pathname],bundle:true,write:false,format:'iife',platform:'browser'});
const exercise={id:'num-01',topic:'numbers',title:'Read the bits',prompt:'Convert binary to decimal.',input_help:'Give a decimal value.',references:[]};
async function harness(progress={},fail=false){
 const dom=new JSDOM(html,{url:'https://backbone.example/practice.html',runScripts:'outside-only'});
 const requests=[];
 dom.window.fetch=async(path,options={})=>{
  const body=options.body?JSON.parse(options.body):null;requests.push({path,body});
  if(path.endsWith('/state'))return {ok:true,json:async()=>({session_id:'demo',exercises:[exercise],progress,actions:[]})};
  if(path.endsWith('/draft'))return {ok:!fail,status:fail?503:200,json:async()=>fail?{detail:'Offline; keep your work.'}:{revision:1}};
  if(path.endsWith('/check'))return {ok:true,json:async()=>({status:'correct',message:'Correct value.',sources:[]})};
  if(path.endsWith('/events'))return {ok:true,json:async()=>({events:[{seq:1,at:'2026-11-14T12:00:00Z',kind:'draft_saved',exercise_id:'num-01',payload:{answer:'<script>bad</script>',work:'place values'}}]})};
  throw Error('Unexpected request');
 };
 dom.window.eval((await bundle).outputFiles[0].text);await tick();
 return {dom,doc:dom.window.document,requests};
}
test('refresh restores saved work and sends the displayed attempt before checking',async()=>{
 const h=await harness({'num-01':{answer:'45',work:'32+8+4+1',revision:0,completed:false}});
 try{
  assert.equal(h.doc.querySelector('#practice-answer').value,'45');
  assert.equal(h.doc.querySelector('#practice-work').value,'32+8+4+1');
  h.doc.querySelector('#practice-check').click();await tick();await tick();
  assert.equal(h.requests.find(r=>r.path.endsWith('/check')).body.answer,'45');
  assert.match(h.doc.querySelector('#practice-feedback').textContent,/Correct value/);
 }finally{h.dom.window.close()}
});
test('failed saving preserves visible work and stops checking',async()=>{
 const h=await harness({},true);
 try{
  const input=h.doc.querySelector('#practice-answer');input.value='45';input.dispatchEvent(new h.dom.window.Event('input'));
  h.doc.querySelector('#practice-check').click();await tick();await tick();
  assert.equal(input.value,'45');
  assert.match(h.doc.querySelector('#practice-error').textContent,/Offline/);
  assert.equal(h.requests.filter(r=>r.path.endsWith('/check')).length,0);
 }finally{h.dom.window.close()}
});
test('replay renders submitted work literally',async()=>{
 const h=await harness();
 try{
  h.doc.querySelector('#practice-replay').click();await tick();
  assert.match(h.doc.querySelector('#replay-event').textContent,/<script>bad<\/script>/);
  assert.equal(h.doc.querySelector('#replay-event script'),null);
 }finally{h.dom.window.close()}
});
