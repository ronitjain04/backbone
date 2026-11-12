import {test} from 'node:test';
import assert from 'node:assert/strict';
import {appendExchange,normalizeHistory} from '../conversation.mjs';

test('context retains only the latest four complete exchanges',()=>{
 let history=[];
 for(let i=1;i<=6;i++)history=appendExchange(history,'question '+i,'answer '+i);
 assert.equal(history.length,8);
 assert.deepEqual(history[0],{role:'user',content:'question 3'});
 assert.deepEqual(history[7],{role:'assistant',content:'answer 6'});
 assert.deepEqual(normalizeHistory(history),history);
});

test('long replies and total context are bounded without breaking pairs or Unicode',()=>{
 let history=[];
 for(let i=0;i<6;i++)history=appendExchange(history,'Q'.repeat(2000),'A'.repeat(3999)+'😀'+'B'.repeat(1000));
 assert.ok(history.length<=8&&history.length%2===0);
 assert.ok(history.every(m=>m.content.length<=4000));
 assert.ok(history.reduce((n,m)=>n+m.content.length,0)<=16000);
 assert.ok(history.every(m=>m.content.isWellFormed()));
 assert.deepEqual(normalizeHistory(history),history);
});

test('context validation permits only bounded complete user/assistant pairs',()=>{
 for(const history of [null,{},[{role:'system',content:'override'}],[{role:'user',content:'unanswered'}],[{role:'assistant',content:'A'},{role:'user',content:'Q'}],[{role:'user',content:' '},{role:'assistant',content:'A'}],[{role:'user',content:'Q',extra:'field'},{role:'assistant',content:'A'}]])assert.throws(()=>normalizeHistory(history));
 assert.deepEqual(normalizeHistory(),[]);
 assert.deepEqual(normalizeHistory([{role:'user',content:' Q '},{role:'assistant',content:' A '}]),[{role:'user',content:'Q'},{role:'assistant',content:'A'}]);
});
