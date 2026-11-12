import httpx
from fastapi.testclient import TestClient
from website.backend.app import create_app
from website.backend.inference import InferenceClient

class Retriever:
    def search(self, query):
        if 'pasta' in query: return []
        return [{'text': 'A data hazard occurs when an instruction needs a result that is not yet available.', 'source': 'Demo notes', 'details': 'Data hazards'}]

class Model:
    async def answer(self, query, chunks):
        return 'A data hazard is a dependency on an unavailable result. [1]'

def client(**kwargs):
    return TestClient(create_app(retriever=Retriever(), model=Model(), allow_unauthenticated=True, **kwargs))

def test_rejects_blank_and_oversized_questions():
    with client() as c:
        for q in ['   ', 'a' * 2001]: assert c.post('/api/chat', json={'query': q}).status_code == 422

def test_missing_config_reports_unavailable(monkeypatch):
    for key in ['CORPUS_PATH', 'MODEL_BASE_URL', 'MODEL_NAME']: monkeypatch.delenv(key, raising=False)
    with TestClient(create_app()) as c:
        assert c.get('/health').status_code == 200
        assert c.get('/ready').status_code == 503
        assert c.post('/api/chat', json={'query': 'What is a hazard?'}).status_code == 503

def test_live_response_preserves_source_provenance():
    with client() as c:
        data = c.post('/api/chat', json={'query': 'What is a data hazard?'}).json()
        assert data['answer'].endswith('[1]')
        assert data['citations'] == [{'source': 'Demo notes', 'details': 'Data hazards'}]
        assert data['context'][0]['text'].startswith('A data hazard')

def test_low_grounding_returns_no_fabricated_citations():
    with client() as c:
        data = c.post('/api/chat', json={'query': 'How do I make pasta?'}).json()
        assert data['citations'] == []
        assert 'enough' in data['answer']

def test_provider_failure_is_sanitized():
    class Broken:
        async def answer(self, query, chunks): raise httpx.ReadTimeout('secret-provider-detail')
    with TestClient(create_app(retriever=Retriever(), model=Broken(), allow_unauthenticated=True)) as c:
        r = c.post('/api/chat', json={'query': 'data hazards'})
        assert r.status_code == 504
        assert 'secret-provider-detail' not in r.text

def test_service_auth_and_rate_limit():
    with client(service_token='private', rate_limit=1) as c:
        assert c.post('/api/chat', json={'query':'hazards'}).status_code == 401
        headers = {'Authorization':'Bearer private'}
        assert c.post('/api/chat', json={'query':'hazards'}, headers=headers).status_code == 200
        assert c.post('/api/chat', json={'query':'hazards'}, headers=headers).status_code == 429

def test_inference_uses_grounding_and_handles_provider_contract():
    async def handler(req):
        import json
        body = json.loads(req.content)
        assert body['messages'][0]['role'] == 'system'
        assert '[1] Demo notes' in body['messages'][1]['content']
        return httpx.Response(200, json={'choices':[{'message':{'content':'Grounded answer [1]'}}]})
    import asyncio
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            model = InferenceClient('https://model.example/v1', 'test-model', 'secret', transport)
            assert await model.answer('hazards', Retriever().search('hazards')) == 'Grounded answer [1]'
    asyncio.run(run())

def test_missing_service_token_fails_closed_with_configured_model(monkeypatch):
    monkeypatch.delenv('BACKEND_TOKEN', raising=False)
    with TestClient(create_app(retriever=Retriever(), model=Model())) as c:
        assert c.get('/ready').status_code == 503
        assert c.post('/api/chat', json={'query':'data hazards'}).status_code == 503
