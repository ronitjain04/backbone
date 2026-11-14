from website.backend.practice.bank import load_bank, fingerprint
from website.backend.practice.hints import make_hint, grounded_chunks

class Retriever:
    def __init__(self,chunks):self.chunks=chunks;self.queries=[]
    def search(self,q):self.queries.append(q);return self.chunks

def fixture():
    chunk={'source':'Book','details':'p. 1','text':'Binary positions have powers of two as weights.'}
    e=dict(load_bank()['num-01'],references=[{'source':chunk['source'],'details':chunk['details'],'fingerprint':fingerprint(chunk)}])
    return e,Retriever([chunk])

def test_progressive_hints_have_verified_sources_without_final_answer():
    e,r=fixture()
    hints=[make_hint(e,i,[],r) for i in (1,2,3)]
    assert all(h['status']=='hint' and h['sources'][0]['details']=='p. 1' for h in hints)
    assert len({h['message'] for h in hints})==3
    assert all('45' not in h['message'] for h in hints)
    assert '? [1]' in hints[0]['message']

def test_missing_or_changed_source_prevents_ungrounded_hint():
    e,r=fixture();r.chunks[0]['text']='Changed'
    assert make_hint(e,1,[],r)['status']=='unavailable'
    assert make_hint(e,1,[],None)['status']=='unavailable'

def test_prior_misconception_changes_the_guidance_and_retrieval_query():
    e,r=fixture()
    attempts=[{'input':{'answer':'46','work':'32 + 8 = 41'},'result':{'misconception':{'label':'Arithmetic error','evidence':'32 + 8 = 41'}}}]
    result=make_hint(e,2,attempts,r)
    assert '32 + 8 = 41' in result['message']
    assert 'Arithmetic error' in r.queries[-1]
