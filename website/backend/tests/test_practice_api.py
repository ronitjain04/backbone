import os
import pytest
from fastapi.testclient import TestClient
from website.backend.app import create_app
from website.backend.site import create_site
from website.backend.practice.store import Store
from website.backend.practice.bank import load_bank

@pytest.fixture
def practice():
    if not os.getenv('TEST_DATABASE_URL'):pytest.skip('Real PostgreSQL required')
    store=Store(os.environ['TEST_DATABASE_URL']);store.migrate();store.seed(load_bank())
    app=create_site(create_app(),practice_store=store)
    with TestClient(app) as client:
        yield client,store
        if client.cookies.get('backbone_student'):client.post('/api/practice/delete',headers={'Origin':'http://testserver'})


def test_student_api_restores_draft_and_never_exposes_answer_keys(practice):
    client,store=practice
    assert client.get('/api/practice/state').status_code==401
    start=client.post('/api/practice/start',json={'name':'Demo'},headers={'Origin':'http://testserver'})
    assert start.status_code==200
    assert 'HttpOnly' in start.headers['set-cookie']
    state=start.json()
    assert len([e for e in state['exercises'] if not e['id'].endswith('-follow')])==18
    assert all('answer' not in e and 'hints' not in e for e in state['exercises'])
    saved=client.post('/api/practice/draft',json={'exercise_id':'num-01','answer':'32+8+4+1','work':'sum the set bits','revision':0},headers={'Origin':'http://testserver'})
    assert saved.status_code==200
    assert client.get('/api/practice/state').json()['progress']['num-01']['answer']=='32+8+4+1'
    assert client.post('/api/practice/draft',json={'exercise_id':'num-01','answer':'stale','revision':0},headers={'Origin':'http://testserver'}).status_code==409
    assert client.get('/api/practice/events').json()['events'][-1]['kind']=='draft_saved'


def test_cross_origin_and_classroom_access_are_rejected(practice):
    client,_=practice
    assert client.post('/api/practice/start',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/practice/classroom').status_code==401
    assert client.post('/api/practice/start',content='x'*33000,headers={'Origin':'http://testserver','Content-Type':'application/json'}).status_code==413
