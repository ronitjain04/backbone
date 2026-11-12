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
});
