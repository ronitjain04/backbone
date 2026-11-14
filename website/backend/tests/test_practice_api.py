import os
import pytest
from fastapi.testclient import TestClient
from website.backend.app import create_app
from website.backend.site import create_site
from website.backend.practice.store import Store
from website.backend.practice.bank import load_bank

@pytest.fixture
def practice(practice_database_url):
    store=Store(practice_database_url);store.migrate();store.seed(load_bank())
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

def test_checks_hints_and_replay_persist_across_requests(practice):
    from website.backend.retrieval import Retriever
    client,store=practice
    origin={'Origin':'http://testserver'}
    client.post('/api/practice/start',json={},headers=origin)
    action={'exercise_id':'num-01','answer':'45','work':'','request_key':'check-unique-001'}
    checked=client.post('/api/practice/check',json=action,headers=origin)
    assert checked.status_code==200
    assert checked.json()['status']=='correct'
    assert client.post('/api/practice/check',json=action,headers=origin).json()==checked.json()
    assert client.get('/api/practice/state').json()['progress']['num-01']['completed'] is True
    events=client.get('/api/practice/events').json()['events']
    assert [e['kind'] for e in events].count('check_requested')==1
    assert events[-1]['kind']=='check_finished'
    # No private course corpus is configured in this API fixture: hints must fail honestly.
    hinted=client.post('/api/practice/hint',json={**action,'request_key':'hint-unique-001'},headers=origin)
    assert hinted.json()['status']=='unavailable'
    assert client.get('/api/practice/state').json()['progress']['num-01']['hint_level']==0


def test_numeric_error_does_not_invent_a_misconception(practice):
    client,_=practice;origin={'Origin':'http://testserver'}
    client.post('/api/practice/start',json={},headers=origin)
    result=client.post('/api/practice/check',json={'exercise_id':'num-01','answer':'46','work':'','request_key':'wrong-answer-001'},headers=origin).json()
    assert result['status']=='incorrect'
    assert result['misconception'] is None
    assert result['clarification']


def test_owner_can_replay_but_students_cannot_enumerate_peers(practice,monkeypatch):
    client,_=practice;monkeypatch.setenv('PRACTICE_OWNER_TOKEN','owner-test-only')
    client.post('/api/practice/start',json={},headers={'Origin':'http://testserver'})
    assert client.get('/api/practice/classroom').status_code==401
    sessions=client.get('/api/practice/classroom',headers={'X-Practice-Owner':'owner-test-only'}).json()['sessions']
    sid=client.get('/api/practice/state').json()['session_id']
    assert sid in [s['id'] for s in sessions]
    assert client.get(f'/api/practice/classroom/{sid}/events').status_code==401
    assert client.get(f'/api/practice/classroom/{sid}/events',headers={'X-Practice-Owner':'owner-test-only'}).json()['events'][0]['kind']=='session_started'

def test_overflow_requires_explanation_before_completion(practice):
    client,_=practice;origin={'Origin':'http://testserver'}
    client.post('/api/practice/start',json={},headers=origin)
    result=client.post('/api/practice/check',json={'exercise_id':'num-05','answer':'yes','work':'','request_key':'needs-explanation-001'},headers=origin).json()
    assert result['status']=='needs_clarification'
    assert client.get('/api/practice/state').json()['progress']['num-05']['completed'] is False

def test_startup_can_bootstrap_practice_without_exposing_migrations(practice_database_url,monkeypatch):
    monkeypatch.setenv('PRACTICE_AUTO_MIGRATE','1')
    store=Store(practice_database_url)
    with TestClient(create_site(create_app(),practice_store=store)) as client:
        result=client.post('/api/practice/start',json={},headers={'Origin':'http://testserver'})
        assert result.status_code==200
        assert client.get('/api/practice/migrate').status_code==404
        client.post('/api/practice/delete',headers={'Origin':'http://testserver'})
