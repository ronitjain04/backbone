import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from website.backend.practice.bank import load_bank
from website.backend.practice.store import Store, Conflict, Unauthorized

@pytest.fixture
def store():
    dsn=os.getenv('TEST_DATABASE_URL')
    if not dsn: pytest.skip('Set TEST_DATABASE_URL to a real PostgreSQL test database')
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
