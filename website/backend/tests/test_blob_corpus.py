import asyncio
import base64
import gzip
import json
import pytest
from website.backend.corpus import load_blob_corpus


def test_private_corpus_is_decoded_and_downloaded_once_per_call():
    text=json.dumps({'text':'The bus carries one value.', 'source':'Private note'})
    async def download(path):
        assert path == 'courses/cs2110.jsonl.gz.b64'
        return base64.b64encode(gzip.compress(text.encode()))
    assert asyncio.run(load_blob_corpus('courses/cs2110.jsonl.gz.b64', download=download)) == text


def test_blob_corpus_rejects_unexpected_paths_and_oversized_data():
    async def download(_): return b'x' * (20*1024*1024+1)
    with pytest.raises(ValueError): asyncio.run(load_blob_corpus('https://example.com/file', download=download))
    with pytest.raises(ValueError): asyncio.run(load_blob_corpus('courses/cs2110.jsonl.gz.b64', download=download))


def test_blob_decompression_has_a_limit():
    async def download(_): return base64.b64encode(gzip.compress(b'x'*(20*1024*1024+1)))
    with pytest.raises(ValueError): asyncio.run(load_blob_corpus('courses/cs2110.jsonl.gz.b64', download=download))


def test_private_blob_startup_loads_course_and_keeps_files_private(monkeypatch):
    from fastapi.testclient import TestClient
    from website.backend import app as module
    calls=[]
    async def load(path):
        calls.append(path)
        return json.dumps({'text':'The LC-3 bus carries one value.', 'source':'Private note'})
    class Model:
        async def answer(self, query, chunks, history=None): return 'One value. [1]'
    monkeypatch.setenv('CS2110_CORPUS_BLOB','courses/cs2110.jsonl.gz.b64')
    monkeypatch.setattr(module,'load_blob_corpus',load)
    with TestClient(module.create_app(model=Model(),service_token='test-token')) as client:
        assert client.get('/ready?course=cs2110').status_code == 200
        assert client.get('/courses/cs2110.jsonl.gz.b64').status_code == 404
        assert client.post('/api/chat',json={'query':'bus','course':'cs2110'}).status_code == 401
        answer=client.post('/api/chat',headers={'Authorization':'Bearer test-token'},json={'query':'bus','course':'cs2110'}).json()
        assert answer['course']=='cs2110' and answer['citations']
        assert calls==['courses/cs2110.jsonl.gz.b64']


def test_health_reports_explicit_vercel_release(monkeypatch):
    from fastapi.testclient import TestClient
    from website.backend.app import create_app
    monkeypatch.setenv('BACKBONE_COMMIT','b'*40)
    monkeypatch.setenv('VERCEL_DEPLOYMENT_ID','dpl_example')
    with TestClient(create_app()) as client:
        assert client.get('/health').json()=={'status':'ok','commit':'b'*40,'instance':'dpl_example'}
