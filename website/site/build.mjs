import {mkdir,writeFile} from 'node:fs/promises';
import {createAssets,serveAsset,securityHeaders} from './assets.mjs';
import {build} from 'esbuild';
const assets=await createAssets();
const proxy=(await build({entryPoints:[new URL('proxy.mjs',import.meta.url).pathname],bundle:true,write:false,format:'esm',platform:'browser',target:'es2022'})).outputFiles[0].text;
const worker=proxy+'\nconst assets='+JSON.stringify(assets)+';\nconst securityHeaders='+JSON.stringify(securityHeaders)+';\nconst serveAsset='+serveAsset.toString()+';\nexport default {async fetch(request,env){const path=new URL(request.url).pathname;if(path.startsWith("/api/"))return handleRequest(request,env);return serveAsset(request,assets)}};';
await mkdir(new URL('dist/server/',import.meta.url),{recursive:true});
await writeFile(new URL('dist/server/index.js',import.meta.url),worker);
console.log('Built website and API proxy: dist/server/index.js');
