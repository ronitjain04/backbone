/** The local preview uses the same FastAPI gateway as Vercel. */
import {spawn} from 'node:child_process';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
export function launchGateway({python=process.env.PYTHON||'python3',port=Number(process.env.PORT||4173),root=fileURLToPath(new URL('../..',import.meta.url)),spawnProcess=spawn,log=console.error}={}){
 const child=spawnProcess(python,['-m','uvicorn','website.backend.site:app','--app-dir',root,'--host','127.0.0.1','--port',String(port)],{cwd:root,stdio:'inherit'});
 const help='Install Python 3.12 and website/backend/requirements.txt; set PYTHON to your virtualenv Python. Configure DATABASE_URL for saved practice. See website/README.md.';
 child.on('error',()=>log('Could not start the combined preview. '+help));
 child.on('exit',code=>{if(code)log('The combined preview stopped. '+help)});
 return child;
}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){
 await import('./build-static.mjs');
 const child=launchGateway();
 child.on('error',()=>{process.exitCode=1});
 child.on('exit',code=>{process.exitCode=code??1});
 for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
}
