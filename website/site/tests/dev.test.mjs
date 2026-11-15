import test from 'node:test';
import assert from 'node:assert/strict';
import {EventEmitter} from 'node:events';
import {launchGateway} from '../dev.mjs';
test('local launcher starts the production gateway with repository import root',()=>{
 let called;const child=new EventEmitter();const messages=[];
 launchGateway({python:'test-python',port:4199,root:'/repo',spawnProcess:(...args)=>{called=args;return child},log:m=>messages.push(m)});
 assert.equal(called[0],'test-python');assert.ok(called[1].includes('website.backend.site:app'));
 assert.ok(called[1].includes('/repo'));assert.equal(called[2].stdio,'inherit');
 child.emit('error',new Error('ENOENT'));assert.match(messages.join(' '),/requirements/);
});
