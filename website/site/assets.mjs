import {readFile,readdir} from 'node:fs/promises';
import {build} from 'esbuild';

export const securityHeaders={
 'X-Content-Type-Options':'nosniff',
 'Referrer-Policy':'strict-origin-when-cross-origin',
 // KaTeX uses generated inline style attributes for equation layout.
 'Content-Security-Policy':"default-src 'self'; style-src 'self' https://fonts.googleapis.com; style-src-attr 'unsafe-inline'; font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'self'"
};

export async function createAssets(){
 const assets={};
 for(const [path,type] of [['/index.html','text/html; charset=utf-8'],['/styles.css','text/css; charset=utf-8']]){
  assets[path]={type,body:await readFile(new URL('.'+path,import.meta.url),'utf8')};
 }
 const bundle=await build({entryPoints:[new URL('app.js',import.meta.url).pathname],bundle:true,write:false,minify:true,legalComments:'inline',format:'esm',platform:'browser',target:'es2022'});
 assets['/app.js']={type:'text/javascript; charset=utf-8',body:bundle.outputFiles[0].text};
 const katexRoot=new URL('node_modules/katex/dist/',import.meta.url);
 const mathCss=(await readFile(new URL('katex.min.css',katexRoot),'utf8'))
  .replace(/src:(url\([^)]+\.woff2\) format\("woff2"\)),url\([^)]+\.woff\) format\("woff"\),url\([^)]+\.ttf\) format\("truetype"\)/g,'src:$1');
 assets['/katex.css']={type:'text/css; charset=utf-8',body:mathCss};
 for(const name of await readdir(new URL('fonts/',katexRoot))){
  if(name.endsWith('.woff2'))assets['/fonts/'+name]={type:'font/woff2',encoding:'base64',body:(await readFile(new URL('fonts/'+name,katexRoot))).toString('base64')};
 }
 return assets;
}

export function serveAsset(request,assets){
 if(request.method!=='GET'&&request.method!=='HEAD')return new Response('Method not allowed',{status:405});
 const path=new URL(request.url).pathname;
 const asset=assets[path==='/'?'/index.html':path];
 if(!asset)return new Response('Not found',{status:404});
 let body=null;
 if(request.method!=='HEAD')body=asset.encoding==='base64'?Uint8Array.from(atob(asset.body),c=>c.charCodeAt(0)):asset.body;
 return new Response(body,{headers:{...securityHeaders,'Content-Type':asset.type}});
}
