import {test} from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFile} from 'node:fs/promises';
// Minimal DOM boundary: exercise production event handlers during a pending network call.
function node(){return {value:'',hidden:false,disabled:false,children:[],handlers:{},classList:{add(){},toggle(){}},addEventListener(type,fn){this.handlers[type]=fn},append(...items){this.children.push(...items)},replaceChildren(...items){this.children=items},remove(){},focus(){},setAttribute(){},querySelector(){return null}}}
test('choosing another example while awaiting an answer preserves the submitted question',async()=>{
 const ids=new Map();for(const id of ['#question-form','#question','#messages','#send','#error','#welcome','#clear','#status','#count'])ids.set(id,node());
 const suggestions=[node(),node()];suggestions[0].dataset={question:'First question'};suggestions[1].dataset={question:'Second question'};
 let resolveAnswer;
 const fetch=async path=>path==='/api/status'?{json:async()=>({ready:false})}:await new Promise(resolve=>{resolveAnswer=resolve});
 const document={querySelector:id=>ids.get(id),querySelectorAll:()=>suggestions,createElement:node,createTextNode:text=>text};
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
