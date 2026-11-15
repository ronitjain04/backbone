"""Small hosted evaluation, using authenticated Vercel curl. Never a load test.
Requires a private corpus path and an already authorized Vercel login.
"""
from pathlib import Path
import argparse,json,time,math,subprocess,tempfile
from website.backend.retrieval import Retriever
from website.backend.practice.bank import fingerprint
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url',required=True)
parser.add_argument('--corpus',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--delay-seconds',type=float,default=35)
parser.add_argument('--vercel-cli',default='vercel')
args=parser.parse_args()
base=args.base_url.rstrip('/')
if not base.startswith('https://'):raise SystemExit('Use an HTTPS review deployment')
corpus=Retriever(args.corpus)
anchors={(x['source'],x.get('details',''),fingerprint(x)) for x in corpus.chunks}
cases=[
 ('mem-06','They select the same number of locations. B stores two bytes at each location while A stores one, so B holds twice as much.','','correct','alternative explanation'),
 ('mem-06','The same address width always means the same total storage.','','incorrect','misconception'),
 ('mem-06','Maybe they are equal, but I am unsure what a location stores.','','needs_clarification','ambiguous'),
 ('lc3-06','LD reads the value x0042 from memory at x3010, while LEA puts the address x3010 itself into the register.','','correct','alternative explanation'),
 ('num-01','45','32 + 8 + 4 + 1 = 45','correct','alternative reasoning'),
 ('num-01','46','32 + 8 = 41','incorrect','first supported error'),
]
report={'environment':'hosted Vercel review + isolated Neon branch + existing Groq model + actual private corpus','cases':[]}
def request(path,body=None,jar=None):
 args=[args.vercel_cli,'curl',path,'--deployment',base,'--','--silent','--show-error','--write-out','\nTIMING:%{time_total}','--header','Origin: '+base]
 if jar:args+=['--cookie',jar,'--cookie-jar',jar]
 if body is not None:args+=['--request','POST','--header','Content-Type: application/json','--data',json.dumps(body)]
 result=subprocess.run(args,cwd='website',capture_output=True,text=True,check=True)
 response,timing=result.stdout.rsplit('\nTIMING:',1)
 return json.loads(response),float(timing)*1000
for i,(eid,answer,work,expected,category) in enumerate(cases):
 with tempfile.NamedTemporaryFile(prefix='classroom-cookie-') as jar:
  start,_=request('/api/practice/start',{'name':'Hosted evaluation '+str(i+1)},jar.name)
  assert 'session_id' in start,start
  try:
   data,latency=request('/api/practice/check',{'exercise_id':eid,'answer':answer,'work':work,'request_key':'hosted-eval-check'},jar.name)
   citations=data.get('sources',[]);valid=sum((x['source'],x.get('details',''),fingerprint(x)) in anchors for x in citations)
   evidence=(data.get('misconception') or {}).get('evidence')
   case={'exercise':eid,'category':category,'expected':expected,'actual':data['status'],'matched':data['status']==expected,'latency_ms':round(latency,2),'citations':len(citations),'valid_citations':valid,'evidence_verbatim':not evidence or evidence in answer+'\n'+work,'model':data.get('model','not returned; deterministic check or conservative fallback')}
   report['cases'].append(case);print(json.dumps(case),flush=True)
  finally:request('/api/practice/delete',{},jar.name)
 if i<len(cases)-1:time.sleep(max(0,args.delay_seconds))
values=sorted(x['latency_ms'] for x in report['cases']);report['latency_ms']={'n':len(values),'p50':values[math.ceil(len(values)*.5)-1],'p95':values[math.ceil(len(values)*.95)-1],'max':max(values)}
report['matched']=sum(x['matched'] for x in report['cases']);report['total']=len(cases)
Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
