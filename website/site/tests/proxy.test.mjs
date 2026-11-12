import {test} from 'node:test';
import assert from 'node:assert/strict';
import {handleRequest} from '../proxy.mjs';
const request = (query='hazards',course) => new Request('https://backbone.example/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query,course})});
test('missing upstream is explicitly unavailable', async()=>{assert.equal((await handleRequest(request(), {})).status,503)});
test('rejects invalid questions before forwarding', async()=>{for(const q of ['', ' '.repeat(4), 'a'.repeat(2001)]) assert.equal((await handleRequest(request(q),{})).status,400)});
test('forwards only to configured upstream and keeps auth server side',async()=>{
 const response=await handleRequest(request(),{BACKEND_URL:'https://api.example',BACKEND_TOKEN:'private'}, async(url,options)=>{
 assert.equal(url,'https://api.example/api/chat');assert.equal(options.headers.Authorization,'Bearer private');
 return Response.json({answer:'A hazard [1]',citations:[{source:'Notes',details:'Hazards'}],context:[]});
 });assert.equal(response.status,200);assert.equal((await response.json()).answer,'A hazard [1]');
});
test('sanitizes failures and malformed upstream responses',async()=>{
 for (const response of [new Response('private stack trace',{status:500}),Response.json({wrong:true})]) {
 const r=await handleRequest(request(),{BACKEND_URL:'https://api.example'},async()=>response);
 assert.equal(r.status,502);assert.ok(!(await r.text()).includes('private stack trace'));
 }
});
test('network errors preserve actionable response',async()=>{assert.equal((await handleRequest(request(),{BACKEND_URL:'https://api.example'},async()=>{throw new Error('private')})).status,502)});
test('chunked oversized body is rejected without trusting content length',async()=>{const r=new Request('https://backbone.example/api/chat',{method:'POST',body:'x'.repeat(10001)});assert.equal((await handleRequest(r,{})).status,413)});
test('invalid JSON and wrong methods are rejected',async()=>{assert.equal((await handleRequest(new Request('https://backbone.example/api/chat',{method:'POST',body:'{'}),{})).status,400);assert.equal((await handleRequest(new Request('https://backbone.example/api/chat'),{})).status,405)});
test('status reflects service configuration without exposing credentials',async()=>{const request=new Request('https://backbone.example/api/status');assert.deepEqual(await(await handleRequest(request,{})).json(),{ready:false});const r=await handleRequest(request,{BACKEND_URL:'https://api.example'},async()=>new Response('',{status:200}));assert.deepEqual(await r.json(),{ready:true})});
test('supports the edge runtime without following upstream redirects',async()=>{
 const edgeFetch=async(url,options)=>{if(options.redirect==='error')throw new TypeError('Invalid redirect value');return Response.json({answer:'A grounded explanation',citations:[],context:[]})};
 const status=await handleRequest(new Request('https://backbone.example/api/status'),{BACKEND_URL:'https://api.example'},edgeFetch);
 assert.deepEqual(await status.json(),{ready:true});
 assert.equal((await handleRequest(request(),{BACKEND_URL:'https://api.example'},edgeFetch)).status,200);
 const redirect=async(url,options)=>{assert.equal(options.redirect,'manual');return new Response(null,{status:302,headers:{Location:'https://other.example'}})};
 assert.equal((await handleRequest(request(),{BACKEND_URL:'https://api.example',BACKEND_TOKEN:'private'},redirect)).status,502);
});
test('forwards the chosen course and refuses unknown course IDs before contacting the backend',async()=>{
 const env={BACKEND_URL:'https://api.example'};
 let calls=0;
 const fetcher=async(url,options)=>{calls++;assert.equal(JSON.parse(options.body).course,'cs2110');return Response.json({course:'cs2110',answer:'LC-3 [1]',citations:[],context:[]})};
 assert.equal((await handleRequest(request('memory','cs2110'),env,fetcher)).status,200);
 for(const course of ['cs9999',null,2110,''])assert.equal((await handleRequest(request('memory',course),env,fetcher)).status,400);
 assert.equal(calls,1);
});
test('an old or mismatched backend cannot answer CS 2110 with CS 2200 material',async()=>{
 for(const course of [undefined,'cs2200']){
  const response=await handleRequest(request('memory','cs2110'),{BACKEND_URL:'https://api.example'},async()=>Response.json({course,answer:'Wrong course',citations:[],context:[]}));
  assert.equal(response.status,503);
 }
});
test('readiness is checked for the selected course and old backends cannot advertise CS 2110',async()=>{
 const req=new Request('https://backbone.example/api/status?course=cs2110');
 const env={BACKEND_URL:'https://api.example'};
 const r=await handleRequest(req,env,async url=>{assert.equal(url,'https://api.example/ready?course=cs2110');return Response.json({courses:['cs2110']})});
 assert.deepEqual(await r.json(),{ready:true});
 const legacy=await handleRequest(req,env,async()=>Response.json({status:'configured'}));
 assert.deepEqual(await legacy.json(),{ready:false});
 assert.equal((await handleRequest(new Request('https://backbone.example/api/status?course=other'),env)).status,400);
});
