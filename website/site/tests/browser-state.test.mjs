import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {build} from 'esbuild';
import {JSDOM} from 'jsdom';

const bundle=build({entryPoints:[new URL('../app.js',import.meta.url).pathname],bundle:true,write:false,format:'iife',platform:'browser'});
const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function harness(){
 const dom=new JSDOM(html,{url:'https://backbone.example',runScripts:'outside-only'});
 const pending=new Map(),sent=[];
 dom.window.AbortSignal=AbortSignal;
 dom.window.fetch=async(path,options)=>{
  if(path.startsWith('/api/status'))return {json:async()=>({ready:true})};
  const body=JSON.parse(options.body);sent.push(body);
  return new Promise(resolve=>pending.set(body.course,resolve));
 };
 dom.window.eval((await bundle).outputFiles[0].text);
 await tick();
 const doc=dom.window.document;
 return {dom,doc,pending,sent,
  input:doc.querySelector('#question'),
  select:course=>doc.querySelector(`[data-course="${course}"]`).click(),
  submit:()=>doc.querySelector('form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}))};
}

test('choosing another example while awaiting an answer preserves the submitted question',async()=>{
 const h=await harness();
 try{
  const suggestions=h.doc.querySelectorAll('[data-question]');
  suggestions[0].click();const original=h.input.value;h.submit();suggestions[1].click();
  assert.equal(h.input.value,original);
  h.pending.get('cs2200')({ok:false,json:async()=>({detail:'Service offline'})});await tick();
  assert.equal(h.input.value,original);
  assert.equal(h.doc.querySelector('#error').hidden,false);
 }finally{h.dom.window.close()}
});

test('switching courses isolates drafts, pending responses and clearing',async()=>{
 const h=await harness();
 try{
  h.input.value='2200 draft';h.select('cs2110');assert.equal(h.input.value,'');
  h.input.value='2110 question';h.submit();
  assert.deepEqual(h.sent[0],{query:'2110 question',course:'cs2110'});
  h.select('cs2200');assert.equal(h.input.value,'2200 draft');
  assert.equal(h.doc.querySelector('#send').disabled,false);
  h.pending.get('cs2110')({ok:true,json:async()=>({course:'cs2110',answer:'LC-3 explanation',citations:[],context:[]})});await tick();
  assert.equal(h.input.value,'2200 draft');assert.equal(h.doc.querySelectorAll('.message').length,0);
  h.select('cs2110');assert.equal(h.doc.querySelectorAll('.message').length,2);assert.equal(h.input.value,'');
  h.select('cs2200');h.doc.querySelector('#clear').click();
  h.select('cs2110');assert.equal(h.doc.querySelectorAll('.message').length,2);
 }finally{h.dom.window.close()}
});

test('formats assistant replies while keeping questions and source excerpts literal',async()=>{
 const h=await harness();
 try{
  h.input.value='**my question** <b>literal</b>';h.submit();
  h.pending.get('cs2200')({ok:true,json:async()=>({course:'cs2200',answer:'**A type alias** [1].\n\n```c\ntypedef struct Flight Flight;\n```\n\n\\(2^n\\)',citations:[{source:'Notes <b>literal</b>',details:'Page 1'}],context:[{text:'**Source** <img src=x onerror=alert(1)>'}]})});
  await tick();
  assert.equal(h.doc.querySelector('.assistant .answer-body strong').textContent,'A type alias');
  assert.ok(h.doc.querySelector('.assistant .answer-body .hljs-keyword'));
  assert.ok(h.doc.querySelector('.assistant .answer-body .katex'));
  assert.equal(h.doc.querySelector('.user p').textContent,'**my question** <b>literal</b>');
  assert.equal(h.doc.querySelector('.user b'),null);
  assert.equal(h.doc.querySelector('.source p').textContent,'**Source** <img src=x onerror=alert(1)>');
  assert.equal(h.doc.querySelector('.source img, .source strong'),null);
 }finally{h.dom.window.close()}
});
