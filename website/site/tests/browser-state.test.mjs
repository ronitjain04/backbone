import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
// Minimal DOM boundary: exercise production event handlers during a pending network call.
function node(){return {value:'',hidden:false,disabled:false,children:[],handlers:{},dataset:{},classList:{add(){},toggle(){}},addEventListener(type,fn){this.handlers[type]=fn},append(...items){this.children.push(...items)},replaceChildren(...items){this.children=items},remove(){},focus(){},setAttribute(){},querySelector(){return null}}}
test('choosing another example while awaiting an answer preserves the submitted question',async()=>{
 const ids=new Map();for(const id of ['#question-form','#question','#messages','#send','#error','#welcome','#clear','#status','#count','#course-title','#course-subtitle','#course-source','#course-description','#welcome-description','#welcome-topics','#course-workspace','#question-label'])ids.set(id,node());
 const suggestions=[node(),node()];suggestions[0].dataset={question:'First question'};suggestions[1].dataset={question:'Second question'};
 let resolveAnswer;
 const fetch=async path=>path.startsWith('/api/status')?{json:async()=>({ready:false})}:await new Promise(resolve=>{resolveAnswer=resolve});
 const document={querySelector:id=>ids.get(id),querySelectorAll:selector=>selector==='[data-question]'?suggestions:[],createElement:node,createTextNode:text=>text};
 vm.runInNewContext(await readFile(new URL('../app.js',import.meta.url),'utf8'),{document,fetch,AbortSignal});
 suggestions[0].handlers.click();
 const pending=ids.get('#question-form').handlers.submit({preventDefault(){}});
 assert.equal(ids.get('#question').value,'First question');
 suggestions[1].handlers.click();
 assert.equal(ids.get('#question').value,'First question');
 resolveAnswer({ok:false,json:async()=>({detail:'Service offline'})});await pending;
 assert.equal(ids.get('#question').value,'First question');
 assert.equal(ids.get('#error').hidden,false);
});
test('switching courses isolates drafts, pending responses and clearing',async()=>{
 const ids=new Map();for(const id of ['#question-form','#question','#messages','#send','#error','#welcome','#clear','#status','#count','#course-title','#course-subtitle','#course-source','#course-description','#welcome-description','#welcome-topics','#course-workspace','#question-label'])ids.set(id,node());
 const tabs=[node(),node()];tabs[0].dataset.course='cs2110';tabs[1].dataset.course='cs2200';
 const suggestions=[node(),node(),node()];
 const pending=new Map(),sent=[];
 const fetch=async(path,options)=>{
  if(path.startsWith('/api/status'))return {json:async()=>({ready:true})};
  const body=JSON.parse(options.body);sent.push(body);
  return new Promise(resolve=>pending.set(body.course,resolve));
 };
 const document={querySelector:id=>ids.get(id),querySelectorAll:selector=>selector==='[data-question]'?suggestions:tabs,createElement:node,createTextNode:text=>text};
 vm.runInNewContext(await readFile(new URL('../app.js',import.meta.url),'utf8'),{document,fetch,AbortSignal});
 const submit=()=>ids.get('#question-form').handlers.submit({preventDefault(){}});
 ids.get('#question').value='2200 draft';ids.get('#question').handlers.input();
 tabs[0].handlers.click();
 assert.equal(ids.get('#question').value,'');
 ids.get('#question').value='2110 question';const answer2110=submit();
 assert.deepEqual(sent[0],{query:'2110 question',course:'cs2110'});
 tabs[1].handlers.click();
 assert.equal(ids.get('#question').value,'2200 draft');
 assert.equal(ids.get('#send').disabled,false);
 pending.get('cs2110')({ok:true,json:async()=>({course:'cs2110',answer:'LC-3 explanation',citations:[],context:[]})});await answer2110;
 assert.equal(ids.get('#question').value,'2200 draft');
 assert.equal(ids.get('#messages').children.length,1);
 tabs[0].handlers.click();
 assert.equal(ids.get('#messages').children.length,3);
 assert.equal(ids.get('#question').value,'');
 tabs[1].handlers.click();ids.get('#clear').handlers.click();
 tabs[0].handlers.click();assert.equal(ids.get('#messages').children.length,3);
});
