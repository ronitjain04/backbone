import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from website.backend.practice.bank import load_bank
from website.backend.practice.store import Store, Conflict, Unauthorized

@pytest.fixture
def store(practice_database_url):
    dsn=practice_database_url
    s=Store(dsn); s.migrate(); s.seed(load_bank()); return s


def test_reload_ownership_revisions_and_delete(store):
    token=store.create_student('Demo')
    other=store.create_student('Other')
    try:
        state=store.snapshot(token)
        assert state['progress']=={}
        saved=store.save_draft(token,'num-01','32+8+4+1','place values',0)
        assert saved['revision']==1
        assert Store(store.dsn).snapshot(token)['progress']['num-01']['answer']=='32+8+4+1'
        assert store.snapshot(other)['progress']=={}
        with pytest.raises(Conflict): store.save_draft(token,'num-01','stale','',0)
        with pytest.raises(Unauthorized):store.snapshot('forged')
        store.delete(token)
        with pytest.raises(Unauthorized):store.snapshot(token)
    finally:
        store.delete(other)


def test_idempotent_actions_and_ordered_events(store):
    token=store.create_student('Events')
    try:
        first=store.begin_action(token,'num-01','check','request-0001',{'answer':'45','work':''})
        again=store.begin_action(token,'num-01','check','request-0001',{'answer':'45','work':''})
        assert again['id']==first['id']
        store.finish_action(token,first['id'],{'status':'correct','message':'Correct','misconception':None})
        assert store.begin_action(token,'num-01','check','request-0001',{'answer':'45','work':''})['result']['status']=='correct'
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda i:store.begin_action(token,'num-02','check',f'parallel-{i}',{'answer':'-10','work':''}),range(8)))
        events=store.events(token)
        assert [e['seq'] for e in events]==list(range(1,len(events)+1))
        assert all(e['at'] for e in events)
        assert store.snapshot(token)['progress']['num-01']['completed'] is True
        assert sum(e['kind']=='check_requested' for e in events)==9
    finally:store.delete(token)

def test_selection_is_persistent_and_actions_are_rate_limited(store):
    from website.backend.practice.store import RateLimited
    token=store.create_student('Limits')
    try:
        store.select_exercise(token,'mem-03')
        assert Store(store.dsn).snapshot(token)['selected_exercise']=='mem-03'
        # Twelve distinct actions are allowed; retries with the same ID are free.
        for i in range(12):store.begin_action(token,'num-01','check',f'budget-{i}',{'answer':'45','work':''})
        assert store.begin_action(token,'num-01','check','budget-0',{'answer':'45','work':''})['new'] is False
        with pytest.raises(RateLimited):store.begin_action(token,'num-01','check','budget-13',{'answer':'45','work':''})
    finally:store.delete(token)

def test_hint_levels_are_idempotent_and_stop_at_three(store):
    token=store.create_student('Hints')
    try:
        for i,level in enumerate((1,2,3,3)):
            action=store.begin_action(token,'num-01','hint',f'hint-request-{i}',{'answer':'','work':''})
            assert action['hint_level']==level
            store.finish_action(token,action['id'],{'status':'hint','level':level,'message':'Try this step.','sources':[]})
            assert store.begin_action(token,'num-01','hint',f'hint-request-{i}',{'answer':'','work':''})['result']['level']==level
        assert Store(store.dsn).snapshot(token)['progress']['num-01']['hint_level']==3
        assert len([e for e in store.events(token) if e['kind']=='hint_finished'])==4
    finally:store.delete(token)


def test_expired_inflight_request_can_be_recovered_without_double_hint(store):
    token=store.create_student('Interrupted')
    try:
        a=store.begin_action(token,'num-01','hint','interrupted-001',{'answer':'','work':''})
        with store.connect() as db:db.execute("UPDATE practice_submissions SET created_at=now()-interval '2 minutes' WHERE id=%s",(a['id'],))
        recovered=store.begin_action(token,'num-01','hint','interrupted-001',{'answer':'','work':''})
        assert recovered['result']['status']=='unavailable'
        assert store.snapshot(token)['progress']['num-01']['hint_level']==0
    finally:store.delete(token)

def test_deleting_student_data_does_not_reset_global_request_budget(store):
    token=store.create_student('Disposable')
    store.begin_action(token,'num-01','check','deletion-budget-001',{'answer':'45','work':''})
    with store.connect() as db:before=db.execute("SELECT sum(used) AS n FROM practice_budgets WHERE kind='action'").fetchone()['n']
    store.delete(token)
    with store.connect() as db:after=db.execute("SELECT sum(used) AS n FROM practice_budgets WHERE kind='action'").fetchone()['n']
    assert after==before and before>0
