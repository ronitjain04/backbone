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

def test_corrective_rubric_without_named_misconception_counts_as_help(store):
    t=store.create_student()
    finish(store,t,'mem-06','rubric-000',{'status':'incorrect','message':'Address width counts locations, not bits at a location.','criteria':[{'id':'concept','status':'contradicted','evidence':'same width means same storage'}]})
    assert finish(store,t,'mem-06','correct-00',{'status':'correct'})['outcome']=='corrected_with_help'

def test_expired_pending_hint_resolves_completed_outcome(store):
    t=store.create_student();hint=store.begin_action(t,'num-01','hint','expired-00',{'answer':'','work':''})
    finish(store,t,'num-01','correct-00',{'status':'correct'})
    with store.connect() as db:db.execute("UPDATE practice_submissions SET created_at=now()-interval '2 minutes' WHERE id=%s",(hint['id'],))
    store.begin_action(t,'num-01','hint','expired-00',{'answer':'','work':''})
    assert store.snapshot(t)['progress']['num-01']['outcome']=='solved_independently'

def test_refresh_settles_abandoned_hint_and_late_worker_cannot_deliver_help(store):
    t=store.create_student();hint=store.begin_action(t,'num-01','hint','abandon-00',{'answer':'','work':''})
    finish(store,t,'num-01','correct-00',{'status':'correct'})
    with store.connect() as db:db.execute("UPDATE practice_submissions SET created_at=now()-interval '2 minutes' WHERE id=%s",(hint['id'],))
    assert store.snapshot(t)['progress']['num-01']['outcome']=='solved_independently'
    assert store.finish_action(t,hint['id'],{'status':'hint','level':1,'message':'late help'})['status']=='unavailable'
    assert len([e for e in store.events(t) if e['kind']=='outcome_recorded'])==1
