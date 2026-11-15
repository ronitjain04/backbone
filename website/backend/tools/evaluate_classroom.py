"""Reproducible isolated classroom evaluation. No production load or model calls.

TEST_DATABASE_URL=postgresql://... python -m website.backend.tools.evaluate_classroom --output /tmp/report.json
Creates and removes a uniquely named schema in a LOCAL test database only.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
from uuid import uuid4
from fastapi.testclient import TestClient
from psycopg import connect, sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from website.backend.app import create_app
from website.backend.site import create_site
from website.backend.practice.bank import load_bank, fingerprint
from website.backend.practice.store import Store

class FixtureRetriever:
    def __init__(self,chunk):self.chunks=[chunk]
    def search(self,query):return self.chunks


def percentile(values,p):return round(sorted(values)[max(0,math.ceil(len(values)*p)-1)],2)


def run_classroom(dsn):
    store=Store(dsn);store.migrate();bank=load_bank()
    chunk={'source':'Evaluation fixture','details':'addressability','text':'Address bits count distinct locations. Addressability is the bits stored at each location. Multiply locations by bits per location, then divide by eight for bytes.'}
    for e in (bank['mem-03'],bank['mem-03']['follow_up']):
        e['references']=[{'source':chunk['source'],'details':chunk['details'],'fingerprint':fingerprint(chunk)}]
    store.seed(bank)
    app=create_site(create_app(retrievers={'cs2110':FixtureRetriever(chunk)}),practice_store=store)
    samples=defaultdict(list);statuses=defaultdict(int);tokens=[];owner=os.environ.get('PRACTICE_OWNER_TOKEN','')
    assert owner,'A test-only PRACTICE_OWNER_TOKEN must be set'
    origin={'Origin':'http://testserver'}
    def call(c,method,path,body=None,headers=None):
        start=time.perf_counter();r=c.request(method,'/api/practice/'+path,json=body,headers=headers or origin)
        samples[path.split('/')[0]].append((time.perf_counter()-start)*1000);statuses[r.status_code]+=1;return r
    def student(i):
        with TestClient(app) as c:
            state=call(c,'POST','start',{'name':f'Simulated {i+1:02}'}).json();token=c.cookies.get('backbone_student');tokens.append(token)
            tab=str(uuid4());call(c,'POST','presence',{'tab_id':tab,'sequence':1})
            e='mem-03' if i>=20 else 'num-01';call(c,'POST','select',{'exercise_id':e})
            def action(kind,key,answer,work=''):
                body={'exercise_id':e,'request_key':key,'answer':answer,'work':work}
                r=call(c,'POST',kind,body);assert r.status_code==200,r.text
                # Concurrent duplicate deliveries after completion must return exactly the cached result.
                with ThreadPoolExecutor(max_workers=2) as pool:
                    repeated=list(pool.map(lambda _:call(c,'POST',kind,body),range(2)))
                assert all(x.status_code==200 and x.json()==r.json() for x in repeated)
                return r.json()
            if i>=20:
                assert action('check','wrong-0000','2048 bits','2048 bits = 2048 bytes')['status']=='incorrect'
                assert action('hint','hint-00000','2048 bits')['status']=='hint'
            result=action('check','correct-000',bank[e]['answer']);assert result['status']=='correct'
            assert result['outcome']==('corrected_with_help' if i>=20 else 'solved_independently')
            if i>=20:
                e+='-follow';call(c,'POST','select',{'exercise_id':e});assert action('check','follow-0000',bank['mem-03']['follow_up']['answer'])['outcome']=='solved_independently'
            # Reconnect in a new client while retaining only the real HttpOnly cookie.
            with TestClient(app) as reconnect:
                reconnect.cookies.set('backbone_student',token,path='/api/practice')
                restored=call(reconnect,'GET','state').json();assert restored['progress'][e]['completed']
                call(reconnect,'POST','presence',{'tab_id':tab,'sequence':3})
                call(reconnect,'POST','presence',{'tab_id':tab,'sequence':2,'connected':False})
            return state['session_id']
    started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=10) as pool:
        pending=[pool.submit(student,i) for i in range(30)]
        with TestClient(app) as teacher:
            while not all(f.done() for f in pending):
                r=call(teacher,'GET','classroom',headers={'X-Practice-Owner':owner});assert r.status_code==200
                time.sleep(.05)
        ids=[f.result() for f in pending]
    with store.connect() as db:
        counts={kind:db.execute('SELECT count(*) AS n FROM practice_events WHERE kind=%s',(kind,)).fetchone()['n'] for kind in ('check_requested','hint_requested','outcome_recorded')}
        assert counts=={'check_requested':50,'hint_requested':10,'outcome_recorded':40},counts
        budget=db.execute("SELECT sum(used) AS n FROM practice_budgets WHERE kind='action'").fetchone()['n'];assert budget==60
        outcomes={r['outcome']:r['n'] for r in db.execute('SELECT outcome,count(*) AS n FROM practice_progress WHERE completed GROUP BY outcome')}
        assert outcomes=={'corrected_with_help':10,'solved_independently':30},outcomes
        for sid in ids:
            events=store.classroom_events(sid);assert [e['seq'] for e in events]==list(range(1,len(events)+1))
    return {'environment':'local ASGI + real PostgreSQL; fixture retriever, no model calls','students':30,'action_budget_used':int(budget),'duplicate_http_deliveries':120,'reconnects':30,'event_counts':counts,'outcomes':outcomes,'elapsed_seconds':round(time.perf_counter()-started,2),'http_statuses':dict(statuses),'latency_ms':{k:{'n':len(v),'p50':percentile(v,.5),'p95':percentile(v,.95),'max':round(max(v),2)} for k,v in sorted(samples.items())}}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    dsn=os.environ['TEST_DATABASE_URL'];host=conninfo_to_dict(dsn).get('host','')
    if host not in ('127.0.0.1','localhost'):raise SystemExit('Use an isolated local PostgreSQL database, never a hosted database.')
    schema='classroom_eval_'+uuid4().hex
    with connect(dsn,autocommit=True) as db:db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        os.environ['PRACTICE_OWNER_TOKEN']='local-evaluation-only'
        report=run_classroom(make_conninfo(dsn,options=f'-c search_path={schema}'))
        report['at']=datetime.now(timezone.utc).isoformat();Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        with connect(dsn,autocommit=True) as db:db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
if __name__=='__main__':main()
