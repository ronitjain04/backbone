import {readFile,mkdir,writeFile} from 'node:fs/promises';
const assets={};
for(const [path,type] of [['/index.html','text/html; charset=utf-8'],['/styles.css','text/css; charset=utf-8'],['/app.js','text/javascript; charset=utf-8']]) assets[path]={type,body:await readFile(new URL('.'+path,import.meta.url),'utf8')};
const proxy=await readFile(new URL('proxy.mjs',import.meta.url),'utf8');
const worker=proxy+'\nconst assets='+JSON.stringify(assets)+';\nexport default {async fetch(request,env){const path=new URL(request.url).pathname;if(path.startsWith("/api/"))return handleRequest(request,env);if(request.method!=="GET"&&request.method!=="HEAD")return new Response("Method not allowed",{status:405});const asset=assets[path==="/"?"/index.html":path];if(!asset)return new Response("Not found",{status:404});return new Response(request.method==="HEAD"?null:asset.body,{headers:{"Content-Type":asset.type,"X-Content-Type-Options":"nosniff","Referrer-Policy":"strict-origin-when-cross-origin","Content-Security-Policy":"default-src \'self\'; style-src \'self\' https://fonts.googleapis.com; font-src \'self\' https://fonts.gstatic.com; script-src \'self\'; connect-src \'self\'; img-src \'self\' data:; base-uri \'none\'; form-action \'self\'"}})}};';
await mkdir(new URL('dist/server/',import.meta.url),{recursive:true});
await writeFile(new URL('dist/server/index.js',import.meta.url),worker);
console.log('Built website and API proxy: dist/server/index.js');
