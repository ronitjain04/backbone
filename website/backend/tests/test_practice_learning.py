import pytest
from website.backend.practice.bank import load_bank
from website.backend.practice.store import Store, Conflict

@pytest.fixture
def store(practice_database_url):
    s=Store(practice_database_url);s.migrate();s.seed(load_bank());return s

def finish(s,t,e,key,result,kind='check'):
    a=s.begin_action(t,e,kind,key,{'answer':'','work':''})
    return s.finish_action(t,a['id'],result)

def test_independent_and_helped_transfer(store):
    t=store.create_student('Learning')
    with pytest.raises(Conflict):store.select_exercise(t,'mem-03-follow')
    finish(store,t,'mem-03','wrong-000',{'status':'incorrect','message':'Show a step','clarification':'Show one step'})
    finish(store,t,'mem-03','hint-0000',{'status':'hint','level':1,'message':'Which quantity is per address?'},'hint')
    r=finish(store,t,'mem-03','correct-00',{'status':'correct','message':'Correct'})
    assert r['outcome']=='corrected_with_help'
    store.select_exercise(t,'mem-03-follow')
    r=finish(store,t,'mem-03-follow','transfer-00',{'status':'correct','message':'Correct'})
    assert r['outcome']=='solved_independently'
    finish(store,t,'mem-03-follow','hint-late0',{'status':'hint','level':1,'message':'Help'},'hint')
    assert store.snapshot(t)['progress']['mem-03-follow']['outcome']=='solved_independently'
    assert [e['payload']['outcome'] for e in store.events(t) if e['kind']=='outcome_recorded']==['corrected_with_help','solved_independently']

def test_supported_feedback_is_help_but_clarification_is_not(store):
    t=store.create_student()
    finish(store,t,'num-01','unclear-00',{'status':'needs_clarification','message':'What does this mean?'})
    assert finish(store,t,'num-01','right-000',{'status':'correct','message':'Correct'})['outcome']=='solved_independently'
    finish(store,t,'mem-03','diagnose-0',{'status':'incorrect','misconception':{'label':'Units','evidence':'2048 bits = 2048 bytes'},'message':'Revisit the units'})
    assert finish(store,t,'mem-03','right-001',{'status':'correct','message':'Correct'})['outcome']=='corrected_with_help'

def test_pending_hint_defers_independence_and_failed_hint_does_not_count(store):
    t=store.create_student()
    hint=store.begin_action(t,'num-01','hint','pending-00',{'answer':'','work':''})
    r=finish(store,t,'num-01','right-000',{'status':'correct','message':'Correct'})
    assert r['outcome']=='pending_assistance'
    store.finish_action(t,hint['id'],{'status':'unavailable','message':'Unavailable'})
    assert store.snapshot(t)['progress']['num-01']['outcome']=='solved_independently'

def test_historical_completion_and_migration_rerun(store):
    t=store.create_student();store.select_exercise(t,'num-01')
    with store.connect() as db:db.execute("UPDATE practice_progress SET completed=true,outcome='historical_unclassified' WHERE exercise_id='num-01'")
    store.migrate();store.migrate()
    assert store.snapshot(t)['progress']['num-01']['outcome']=='historical_unclassified'
    with store.connect() as db:assert db.execute('SELECT count(*) AS n FROM practice_migrations').fetchone()['n']==2
