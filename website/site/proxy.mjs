const json=(body,status=200)=>Response.json(body,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
export async function handleRequest(request,env,fetcher=fetch){
 const path=new URL(request.url).pathname;
 if(path==='/api/status'){
  if(!env.BACKEND_URL) return json({ready:false});
  try{const r=await fetcher(env.BACKEND_URL.replace(/\/$/,'')+'/ready',{signal:AbortSignal.timeout(5000),redirect:'error'});return json({ready:r.ok})}catch{return json({ready:false})}
 }
 if(path!=='/api/chat') return json({detail:'Not found'},404);
 if(request.method!=='POST') return json({detail:'Method not allowed'},405);
 if(Number(request.headers.get('Content-Length'))>10000) return json({detail:'Question too large.'},413);
 let data;
 try{
  // Bound chunked bodies too; Content-Length is not guaranteed.
  const reader=request.body?.getReader();let size=0;const chunks=[];
  if(!reader)throw Error();
  while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>10000){await reader.cancel();return json({detail:'Question too large.'},413)}chunks.push(value)}
  const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length}
  data=JSON.parse(new TextDecoder().decode(bytes));
 }catch{return json({detail:'Enter a valid question.'},400)}
 if(typeof data?.query!=='string'||!data.query.trim()||data.query.length>2000)return json({detail:'Enter a question of 1–2,000 characters.'},400);
 if(!env.BACKEND_URL)return json({detail:'Live answers are not connected yet. The website is ready; a hosted model service still needs to be configured.'},503);
 try{
  const headers={'Content-Type':'application/json'};
  if(env.BACKEND_TOKEN)headers.Authorization='Bearer '+env.BACKEND_TOKEN;
  const response=await fetcher(env.BACKEND_URL.replace(/\/$/,'')+'/api/chat',{method:'POST',headers,body:JSON.stringify({query:data.query.trim()}),signal:AbortSignal.timeout(70000),redirect:'error'});
  if(!response.ok){const status=[429,503,504].includes(response.status)?response.status:502;return json({detail:status===429?'Backbone is busy. Give it a minute, then try again.':status===503?'The course and model service are still being connected. Please try again later.':status===504?'The model took too long. Please try again.':'The answer service is unavailable. Your question is saved below.'},status)}
  const result=await response.json();
  if(typeof result.answer!=='string'||!Array.isArray(result.citations)||!Array.isArray(result.context))return json({detail:'The answer service returned an invalid response. Please try again.'},502);
  return json(result);
 }catch(error){return json({detail:error.name==='TimeoutError'?'The model took too long. Please try again.':'Could not reach the answer service. Your question is saved below.'},error.name==='TimeoutError'?504:502)}
}
