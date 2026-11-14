from uuid import uuid4
import pytest
from website.backend.practice.store import Store, Conflict
from website.backend.practice.bank import load_bank
from website.backend.practice.visual import explanation
from website.backend.practice.classroom import presence_label

@pytest.fixture
def store(practice_database_url):
    s=Store(practice_database_url);s.migrate();s.seed(load_bank());return s

def test_presence_order_multiple_tabs_and_thresholds(store):
    t=store.create_student();a,b=str(uuid4()),str(uuid4())
    store.presence(t,a,2,True);store.presence(t,a,1,False)
    assert store.classroom()[0]['presence']=='active'
    store.presence(t,b,1,True);store.presence(t,a,3,False)
    assert store.classroom()[0]['presence']=='active'
    store.presence(t,b,2,False)
    assert store.classroom()[0]['presence']=='disconnected'
    assert [presence_label(x,True) for x in (44,45,120,121)]==['active','stale','stale','disconnected']
    assert len([e for e in store.events(t) if e['kind']=='presence_changed'])==4

def test_visual_idempotency_restore_and_helped_outcome(store):
    t=store.create_student();e=store.exercise(t,'mem-03')
    payload={'stage':1,'address_bits':2,'bits_per_location':4}
    r=explanation(e,1,[],[{'source':'text','details':'1','text':'Addressability is the bits at one address.'}])
    assert '2048' not in r['message'] and '2 KiB' not in r['message']
    store.visual(t,'mem-03','visual-000',payload,r)
    store.visual(t,'mem-03','visual-000',payload,r)
    assert len([x for x in store.events(t) if x['kind']=='visual_opened'])==1
    assert store.snapshot(t)['visuals']['mem-03']['stage']==1
    a=store.begin_action(t,'mem-03','check','check-0000',{'answer':'','work':''})
    assert store.finish_action(t,a['id'],{'status':'correct'})['outcome']=='corrected_with_help'
    with pytest.raises(Conflict):store.visual(t,'mem-03','visual-000',{**payload,'stage':2},r)

def test_visual_uncertainty_and_supported_quote():
    e=load_bank()['mem-03']
    r=explanation(e,1,[{'kind':'check','input':{'work':''},'result':{'status':'incorrect','misconception':None}}],[{'source':'book'}])
    assert r['evidence'] is None and r['clarification']
    a={'kind':'check','input':{'work':'2048 bits = 2048 bytes'},'result':{'status':'incorrect','misconception':{'criterion':'concept','label':'Arithmetic','evidence':'2048 bits = 2048 bytes'}}}
    assert explanation(e,2,[a],[{'source':'book'}])['evidence']['evidence']==a['input']['work']
    a['result']['misconception']['evidence']='invented'
    assert explanation(e,2,[a],[{'source':'book'}])['evidence'] is None
    assert explanation(e,1,[],[])['status']=='unavailable'

def test_classroom_evidence_and_compact_groups(store):
    t=store.create_student('Learner');store.select_exercise(t,'mem-03')
    a=store.begin_action(t,'mem-03','check','wrong-0000',{'answer':'2','work':'2048 bits = 2048 bytes'})
    store.finish_action(t,a['id'],{'status':'incorrect','message':'Revisit the units','misconception':{'criterion':'concept','label':'Arithmetic','evidence':'2048 bits = 2048 bytes','method':'deterministic equality check'},'sources':[{'source':'book','text':'private text'}]})
    row=store.classroom()[0]
    assert row['current_exercise']=='mem-03' and row['diagnosis']['evidence']=='2048 bits = 2048 bytes'
    assert row['group_key']=='memory:capacity:concept' and 'private text' not in str(row)
    detail=store.classroom_detail(row['id'])
    assert detail['attempts'][0]['input']['work']=='2048 bits = 2048 bytes'
    assert 'private text' in str(detail)
