from fastapi.testclient import TestClient
from website.backend.app import create_app
from website.backend.site import create_site

class Retriever:
    def search(self,query): return [{'text':'Pipeline dependencies cause data hazards.','source':'Demo'}]
class Model:
    async def answer(self,query,chunks,history=None): return 'A dependency. [1]'

def site(tmp_path):
    (tmp_path/'index.html').write_text('<html>Backbone</html>')
    backend=create_app(retrievers={'cs2110':Retriever(),'cs2200':Retriever()},model=Model(),service_token='private-test-token')
    return create_site(backend,token='private-test-token',public_dir=tmp_path)

def test_public_site_chat_status_and_private_routes(tmp_path):
    with TestClient(site(tmp_path)) as c:
        assert 'Backbone' in c.get('/').text
        assert c.get('/api/status?course=cs2110').json()=={'ready':True}
        assert c.get('/api/status?course=unknown').status_code==400
        response=c.post('/api/chat',json={'query':'hazards','course':'cs2200'})
        assert response.status_code==200
        assert response.json()['citations']
        assert 'private-test-token' not in response.text
        assert c.get('/backend/data/demo.jsonl').status_code==404
        assert c.get('/.env').status_code==404
        assert c.get('/api/chat').status_code==405
        assert c.get('/').headers['X-Content-Type-Options']=='nosniff'

def test_public_site_rejects_invalid_or_large_streamed_requests(tmp_path):
    with TestClient(site(tmp_path)) as c:
        assert c.post('/api/chat',json={'query':'hazards','course':'unknown'}).status_code==400
        assert c.post('/api/chat',content='invalid').status_code==400
        def body():
            for _ in range(3): yield b'x'*65536
        assert c.post('/api/chat',content=body()).status_code==413

def test_public_site_does_not_disable_backend_auth(tmp_path):
    backend=create_app(retriever=Retriever(),model=Model(),service_token='secret')
    with TestClient(backend) as c:
        assert c.post('/api/chat',json={'query':'hazards'}).status_code==401


def test_missing_runtime_assets_returns_404_after_cdn_extraction(tmp_path):
    backend=create_app(retriever=Retriever(),model=Model(),service_token='secret')
    with TestClient(create_site(backend,token='secret',public_dir=tmp_path/'missing')) as c:
        assert c.get('/private-data/cs2110/cs2110.jsonl.gz.b64').status_code==404
        assert c.get('/backend/data/demo.jsonl').status_code==404
        assert c.get('/.env').status_code==404
        assert c.get('/api/status').json()=={'ready':True}


def test_public_gateway_preserves_safe_provider_retry_timing_for_monitor():
    import httpx
    import pytest
    from urllib.error import HTTPError
    from scripts.monitor import request_with_retry,MonitorError
    class Throttled:
        async def answer(self,*args,**kw):
            response=httpx.Response(429,headers={'Retry-After':'3600','X-Private':'secret-provider-detail'},request=httpx.Request('POST','https://provider.test/secret'))
            raise httpx.HTTPStatusError('secret-provider-detail',request=response.request,response=response)
    backend=create_app(retriever=Retriever(),model=Throttled(),service_token='synthetic-secret')
    with TestClient(create_site(backend,token='synthetic-secret')) as c:
        def request(url,data=None):
            r=c.post('/api/chat',json={'query':'hazards'})
            assert 'secret' not in r.text and 'X-Private' not in r.headers
            if r.status_code>=400:raise HTTPError(url,r.status_code,'sanitized',r.headers,None)
            return r.json()
        with pytest.raises(MonitorError,match='quota'):
            request_with_retry('https://public.test',request=request,sleep=lambda _:pytest.fail('Must not retry before 3600 seconds'))


def test_public_gateway_preserves_local_retry_after():
    backend=create_app(retriever=Retriever(),model=Model(),service_token='synthetic',rate_limit=1)
    with TestClient(create_site(backend,token='synthetic')) as c:
        assert c.post('/api/chat',json={'query':'hazards'}).status_code==200
        r=c.post('/api/chat',json={'query':'hazards'})
        assert r.status_code==429 and r.headers.get('Retry-After')=='60'


def test_retry_header_sanitization_never_echoes_untrusted_header_text():
    from website.backend.retry import sanitized_retry_after
    assert sanitized_retry_after('3600')=='3600'
    assert sanitized_retry_after('0')=='0'
    assert sanitized_retry_after('secret\r\nX-Private: secret')=='60'
    assert sanitized_retry_after(None)=='60'
    assert sanitized_retry_after('Wed, 21 Oct 2015 07:28:00 GMT')=='0'
