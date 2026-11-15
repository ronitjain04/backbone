"""Synthetic-only browser fixture. This file is outside the Vercel project root."""
import json
from psycopg.conninfo import conninfo_to_dict
from website.backend.app import create_app
from website.backend.site import create_site
from website.backend.practice.bank import load_bank, fingerprint
from website.backend.practice.store import Store

TEACHER_TOKEN='synthetic-browser-teacher'
CHUNK={'source':'Synthetic browser notes','details':'Fixture 1','text':'Address bits count distinct locations. Addressability is bits per location. Total bits equals locations times bits per location. Eight bits make one byte. Binary places have powers of two.'}

class FixtureRetriever:
    chunks=[CHUNK]
    def search(self,query):return self.chunks

class FixtureModel:
    model='synthetic-browser-model'
    async def rewrite_query(self,query,history):return query
    async def answer(self,query,chunks,history=None):return 'Synthetic explanation using the fixture notes. [1]'
    async def assess_practice(self,content):
        data=json.loads(content);text=data['work'] or data['final_answer']
        return json.dumps({'criteria':[{'id':r['id'],'status':'met','evidence':text,'source_ids':[1]} for r in data['rubric']], 'message':'The synthetic reasoning check is consistent.','misconceptions':[]})

def create_fixture_app(dsn):
    if 'practice_test_' not in conninfo_to_dict(dsn).get('options',''):
        raise RuntimeError('Browser fixtures require an isolated synthetic test schema.')
    store=Store(dsn);store.migrate();bank=load_bank()
    for parent in bank.values():
        for e in (parent,parent['follow_up']):e['references']=[{'source':CHUNK['source'],'details':CHUNK['details'],'fingerprint':fingerprint(CHUNK)}]
    store.seed(bank)
    backend=create_app(retrievers={'cs2110':FixtureRetriever(),'cs2200':FixtureRetriever()},model=FixtureModel(),service_token='synthetic-service')
    return create_site(backend,token='synthetic-service',practice_store=store)
