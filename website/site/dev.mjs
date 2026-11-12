import http from 'node:http';
import {handleRequest} from './proxy.mjs';
import {createAssets,serveAsset} from './assets.mjs';
const assets=await createAssets();
const server=http.createServer(async(req,res)=>{try{const path=new URL(req.url,'http://localhost').pathname;let result;if(path.startsWith('/api/')){const chunks=[];let size=0;for await(const c of req){size+=c.length;if(size>10000){res.writeHead(413);res.end('Question too large');return}chunks.push(c)}const body=Buffer.concat(chunks);result=await handleRequest(new Request('http://localhost'+req.url,{method:req.method,headers:req.headers,...(body.length?{body}:{} )}),process.env)}else{result=serveAsset(new Request('http://localhost'+req.url,{method:req.method}),assets)}res.writeHead(result.status,Object.fromEntries(result.headers));res.end(Buffer.from(await result.arrayBuffer()))}catch{res.writeHead(500);res.end('Local server error')}});
server.listen(Number(process.env.PORT||4173),'127.0.0.1',()=>console.log('Backbone preview: http://127.0.0.1:'+(process.env.PORT||4173)));
