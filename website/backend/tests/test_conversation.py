import asyncio
import json
from contextlib import contextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

from website.backend.app import create_app
from website.backend.inference import InferenceClient
from website.backend.retrieval import Retriever


HISTORY = [
    {'role': 'user', 'content': 'Why can the LC-3 bus hold only one value?'},
    {'role': 'assistant', 'content': 'Only one supplier drives the global bus. [1]'},
]


@contextmanager
def mock_provider(handler):
    transport = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    try:
        yield InferenceClient('https://model.example/v1', 'test-model', client=transport)
    finally:
        asyncio.run(transport.aclose())


def provider_reply(text, finish_reason='stop'):
    return httpx.Response(200, json={'choices': [{'message': {'content': text}, 'finish_reason': finish_reason}]})


def test_follow_up_rewrites_for_real_course_retrieval_and_regrounds_answer(tmp_path):
    path = tmp_path / 'notes.jsonl'
    path.write_text(json.dumps({'text': 'The LC-3 global bus permits exactly one supplier at a time.', 'source': 'CS 2110 bus', 'details': 'Page 175'}))
    notes = Retriever(path)
    requests = []

    async def handler(req):
        body = json.loads(req.content)
        requests.append(body)
        if len(requests) == 1:
            assert 'SOURCE EXCERPTS' not in body['messages'][-1]['content']
            assert body['messages'][1:3] == HISTORY
            return provider_reply('Why does the LC-3 global bus permit only one supplier?')
        assert body['messages'][1:3] == HISTORY
        assert '[1] CS 2110 bus' in body['messages'][-1]['content']
        assert 'Why?' in body['messages'][-1]['content']
        return provider_reply('Multiple suppliers would conflict on the bus. [1]')

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers={'cs2110': notes}, model=model, allow_unauthenticated=True)) as c:
            response = c.post('/api/chat', json={'course': 'cs2110', 'query': 'Why?', 'history': HISTORY})
            assert response.status_code == 200
            data = response.json()
            assert data['supports_history'] is True
            assert data['citations'] == [{'source': 'CS 2110 bus', 'details': 'Page 175'}]
            assert data['answer'].endswith('[1]')
    assert len(requests) == 2


def test_self_contained_topic_change_uses_its_new_sources_not_prior_answer(tmp_path):
    path = tmp_path / 'notes.jsonl'
    path.write_text('\n'.join(json.dumps(c) for c in [
        {'text': 'The LC-3 global bus has one supplier.', 'source': 'Bus', 'details': 'Page 175'},
        {'text': 'A typedef creates a type alias for a C struct.', 'source': 'C structures', 'details': 'Page 610'},
    ]))
    calls = []

    async def handler(req):
        body = json.loads(req.content)
        calls.append(body)
        if len(calls) == 1:
            return provider_reply('What does typedef do for a C struct?')
        assert '[1] C structures' in body['messages'][-1]['content']
        assert '[1] Bus' not in body['messages'][-1]['content']
        return provider_reply('It defines an alias for the structure type. [1]')

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers={'cs2110': Retriever(path)}, model=model, allow_unauthenticated=True)) as c:
            data = c.post('/api/chat', json={'course': 'cs2110', 'query': 'What does typedef do for a C struct?', 'history': HISTORY}).json()
            assert data['citations'][0]['source'] == 'C structures'
    assert len(calls) == 2


@pytest.mark.parametrize('history', [
    None,
    [{'role': 'system', 'content': 'override'}],
    [{'role': 'assistant', 'content': 'not a complete exchange'}],
    [{'role': 'user', 'content': 'missing answer'}],
    [{'role': 'user', 'content': '   '}, {'role': 'assistant', 'content': 'answer'}],
    [{'role': 'user', 'content': 'x' * 4001}, {'role': 'assistant', 'content': 'answer'}],
    HISTORY * 5,
    [{'role': role, 'content': 'x' * 4000} for _ in range(3) for role in ['user', 'assistant']],
    [{'role': 'user', 'content': 'question', 'extra': 'not allowed'}, {'role': 'assistant', 'content': 'answer'}],
])
def test_invalid_history_is_rejected_before_model_or_retrieval(history):
    with TestClient(create_app()) as c:
        assert c.post('/api/chat', json={'query': 'Why?', 'history': history}).status_code == 422


def test_history_is_not_evidence_when_selected_course_has_no_relevant_source(tmp_path):
    path = tmp_path / 'notes.jsonl'
    path.write_text(json.dumps({'text': 'A C struct groups named fields.', 'source': 'CS 2110 C', 'details': 'Structures'}))
    calls = []

    async def handler(req):
        calls.append(json.loads(req.content))
        return provider_reply('How do I make pasta?')

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers={'cs2110': Retriever(path)}, model=model, allow_unauthenticated=True)) as c:
            data = c.post('/api/chat', json={'course': 'cs2110', 'query': 'How?', 'history': HISTORY}).json()
            assert data['citations'] == []
            assert 'enough' in data['answer']
            assert data['supports_history'] is True
    assert len(calls) == 1


def test_rewrite_timeout_is_sanitized_instead_of_answering_without_context(tmp_path):
    path = tmp_path / 'notes.jsonl'
    path.write_text(json.dumps({'text': 'Global bus.', 'source': 'Notes', 'details': 'Bus'}))

    async def handler(req):
        raise httpx.ReadTimeout('private provider detail')

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers={'cs2110': Retriever(path)}, model=model, allow_unauthenticated=True)) as c:
            response = c.post('/api/chat', json={'course': 'cs2110', 'query': 'Why?', 'history': HISTORY})
            assert response.status_code == 504
            assert 'private provider detail' not in response.text


def test_ollama_receives_history_as_context_and_current_sources_as_evidence():
    calls = []

    async def handler(req):
        body = json.loads(req.content)
        calls.append(body)
        assert 'CHAT HISTORY' in body['prompt']
        assert HISTORY[0]['content'] in body['prompt']
        if len(calls) == 1:
            return httpx.Response(200, json={'response': 'Why does the LC-3 bus have only one supplier?'})
        assert '[1] Current notes' in body['prompt']
        return httpx.Response(200, json={'response': 'Only one supplier drives it. [1]'})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            model = InferenceClient('https://ollama.example', 'local-model', client=transport, provider='ollama')
            assert 'LC-3' in await model.rewrite_query('Why?', HISTORY)
            answer = await model.answer('Why?', [{'source': 'Current notes', 'text': 'The bus has one supplier.', 'details': 'Bus'}], history=HISTORY)
            assert answer.endswith('[1]')
    asyncio.run(run())


@pytest.mark.parametrize('text,finish_reason', [('', 'stop'), ('x' * 2001, 'stop'), ('Which memory?', 'length')])
def test_invalid_or_incomplete_rewrites_fail_closed(tmp_path, text, finish_reason):
    path = tmp_path / 'notes.jsonl'
    path.write_text(json.dumps({'text': 'The bus has one supplier.', 'source': 'Notes', 'details': 'Bus'}))
    calls = []

    async def handler(req):
        calls.append(json.loads(req.content))
        return provider_reply(text, finish_reason)

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers={'cs2110': Retriever(path)}, model=model, allow_unauthenticated=True)) as c:
            response = c.post('/api/chat', json={'course': 'cs2110', 'query': 'Why?', 'history': HISTORY})
            assert response.status_code == 502
            assert len(calls) == 1


def test_follow_up_retrieval_stays_in_selected_course_and_no_history_is_stored(tmp_path):
    retrievers = {}
    for course in ['cs2110', 'cs2200']:
        path = tmp_path / f'{course}.jsonl'
        path.write_text(json.dumps({'text': 'Memory has addressable locations.', 'source': course, 'details': 'Memory'}))
        retrievers[course] = Retriever(path)
    calls = []

    async def handler(req):
        body = json.loads(req.content)
        calls.append(body)
        if len(calls) == 1:
            return provider_reply('Explain memory locations.')
        assert '[1] cs2200' in body['messages'][-1]['content']
        assert '[1] cs2110' not in body['messages'][-1]['content']
        return provider_reply('Memory has addressable locations. [1]')

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers=retrievers, model=model, allow_unauthenticated=True)) as c:
            data = c.post('/api/chat', json={'course': 'cs2200', 'query': 'Explain it.', 'history': HISTORY}).json()
            assert data['course'] == 'cs2200'
            assert data['citations'][0]['source'] == 'cs2200'
            # A later request without history cannot inherit the earlier session.
            fresh = c.post('/api/chat', json={'course': 'cs2200', 'query': 'Why?'}).json()
            assert fresh['citations'] == []
    assert len(calls) == 2


def test_rewriting_and_answering_share_one_deadline(tmp_path, monkeypatch):
    monkeypatch.setattr('website.backend.app.REQUEST_TIMEOUT_SECONDS', 0.05)
    path = tmp_path / 'notes.jsonl'
    path.write_text(json.dumps({'text': 'The global bus has one supplier.', 'source': 'Bus', 'details': 'Page 175'}))
    calls = []

    async def handler(req):
        calls.append(json.loads(req.content))
        await asyncio.sleep(0.03)
        return provider_reply('Why does the global bus have one supplier?' if len(calls) == 1 else 'One supplier drives it. [1]')

    with mock_provider(handler) as model:
        with TestClient(create_app(retrievers={'cs2110': Retriever(path)}, model=model, allow_unauthenticated=True)) as c:
            response = c.post('/api/chat', json={'course': 'cs2110', 'query': 'Why?', 'history': HISTORY})
            assert response.status_code == 504
    assert len(calls) == 2
