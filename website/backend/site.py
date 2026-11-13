"""Public website gateway. Course data and service credentials stay in-process."""
import os
from contextlib import asynccontextmanager
from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .app import create_app

MAX_REQUEST_BYTES = 128 * 1024


def create_site(backend=None, *, token=None, public_dir=None):
    backend = backend if backend is not None else create_app()
    token = os.getenv('BACKEND_TOKEN', '') if token is None else token
    public_dir = public_dir or Path(__file__).resolve().parent.parent / 'public'

    @asynccontextmanager
    async def lifespan(app):
        async with backend.router.lifespan_context(backend):
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def response_headers(request, call_next):
        if request.url.path == '/api/chat' and request.method != 'POST':
            return JSONResponse({'detail': 'Method not allowed'}, status_code=405)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    async def upstream(method, path, *, content=None):
        # Use an in-process ASGI call, never a public network URL or browser token.
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend), base_url='http://backend') as client:
            return await client.request(method, path, content=content, headers={
                'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token})

    @app.get('/health')
    async def health():
        result = await upstream('GET', '/health')
        return JSONResponse(result.json(), status_code=result.status_code)

    @app.get('/ready')
    async def ready(request: Request):
        result = await upstream('GET', '/ready' + ('?' + request.url.query if request.url.query else ''))
        return JSONResponse(result.json(), status_code=result.status_code)

    @app.get('/api/status')
    async def status(course: str = 'cs2200'):
        if course not in ('cs2110', 'cs2200'):
            return JSONResponse({'detail': 'Choose CS 2110 or CS 2200.'}, status_code=400)
        result = await upstream('GET', '/ready?course=' + course)
        return {'ready': result.status_code == 200 and course in result.json().get('courses', [])}

    @app.post('/api/chat')
    async def chat(request: Request):
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > MAX_REQUEST_BYTES:
                return JSONResponse({'detail': 'Question and conversation context are too large.'}, status_code=413)
            body.extend(chunk)
        result = await upstream('POST', '/api/chat', content=bytes(body))
        if result.status_code == 422:
            return JSONResponse({'detail': 'Enter a valid question, course and conversation context.'}, status_code=400)
        return JSONResponse(result.json(), status_code=result.status_code)

    app.mount('/', StaticFiles(directory=public_dir, html=True, check_dir=False), name='website')
    return app


app = create_site()
