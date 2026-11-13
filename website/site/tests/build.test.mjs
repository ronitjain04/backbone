import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

test('production Worker serves the bundled renderer, styles and local math fonts',async()=>{
 execFileSync(process.execPath,['build.mjs'],{cwd:new URL('..',import.meta.url),stdio:'pipe'});
 const {default:worker}=await import('../dist/server/index.js?test='+Date.now());
 const get=path=>worker.fetch(new Request('https://backbone.example'+path),{});
 const html=await (await get('/')).text();assert.ok(html.includes('href="/katex.css"'));
 const script=await (await get('/app.js')).text();assert.ok(script.includes('answer-body'));
 assert.ok(!script.includes("from './answer-renderer.mjs'"));
 const cssResponse=await get('/katex.css');assert.equal(cssResponse.status,200);
 const css=await cssResponse.text();
 const fontPath='/'+css.match(/url\((fonts\/[^)]+\.woff2)\)/)[1];
 assert.ok(!css.includes('.ttf'));
 const font=await get(fontPath);assert.equal(font.status,200);
 assert.equal(font.headers.get('Content-Type'),'font/woff2');
 assert.equal(new TextDecoder().decode((await font.arrayBuffer()).slice(0,4)),'wOF2');
 const head=await worker.fetch(new Request('https://backbone.example'+fontPath,{method:'HEAD'}),{});
 assert.equal((await head.arrayBuffer()).byteLength,0);
 assert.equal((await get('/not-an-asset')).status,404);
 const csp=(await get('/')).headers.get('Content-Security-Policy');
 assert.ok(csp.includes("script-src 'self'"));
 assert.ok(!csp.includes("script-src 'self' 'unsafe-inline'"));
 const originalFetch=globalThis.fetch;
 try{
  globalThis.fetch=async(url,options)=>{
   assert.equal(url,'https://api.example/api/chat');
   assert.deepEqual(JSON.parse(options.body).history,[{role:'user',content:'Global bus?'},{role:'assistant',content:'One supplier.'}]);
   return Response.json({course:'cs2110',supports_history:true,answer:'A grounded follow-up',citations:[],context:[]});
  };
  const response=await worker.fetch(new Request('https://backbone.example/api/chat',{method:'POST',body:JSON.stringify({query:'Why?',course:'cs2110',history:[{role:'user',content:' Global bus? '},{role:'assistant',content:'One supplier.'}]})}),{BACKEND_URL:'https://api.example'});
  assert.equal(response.status,200);
  assert.equal((await response.json()).answer,'A grounded follow-up');
 }finally{globalThis.fetch=originalFetch}
});

test('Vercel static build contains only browser assets and local math fonts',async()=>{
 const {readFile,readdir}=await import('node:fs/promises');
 execFileSync(process.execPath,['build-static.mjs'],{cwd:new URL('..',import.meta.url),stdio:'pipe'});
 const root=new URL('../../public/',import.meta.url);
 assert.deepEqual((await readdir(root)).sort(),['app.js','fonts','index.html','katex.css','styles.css']);
 assert.ok((await readFile(new URL('index.html',root),'utf8')).includes('Backbone'));
 assert.ok(!(await readFile(new URL('app.js',root),'utf8')).includes('BACKEND_TOKEN'));
 const font=(await readdir(new URL('fonts/',root)))[0];
 assert.equal((await readFile(new URL('fonts/'+font,root))).subarray(0,4).toString(),'wOF2');
});
