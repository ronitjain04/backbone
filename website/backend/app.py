import asyncio
import hmac
import logging
import os
import time
from typing import Literal, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from .inference import InferenceClient
from .retrieval import Retriever

logger=logging.getLogger(__name__)
CourseId = Literal['cs2110', 'cs2200']
class ChatRequest(BaseModel):
    query: str = Field(min_length=1,max_length=2000)
    course: CourseId = 'cs2200'
    @field_validator('query')
    @classmethod
    def nonblank(cls,value):
        if not value.strip(): raise ValueError('Enter a question')
        return value.strip()

def create_app(retriever=None, model=None, service_token=None, rate_limit=10, allow_unauthenticated=False, retrievers=None):
    courses = dict(retrievers or {})
    if retriever is not None:
        courses.setdefault('cs2200', retriever)
    state={'retrievers':courses,'model':model}
    token=service_token if service_token is not None else os.getenv('BACKEND_TOKEN','')
    calls=[]
    @asynccontextmanager
    async def lifespan(app):
        for course in ('cs2110', 'cs2200'):
            path = os.getenv(f'{course.upper()}_CORPUS_PATH')
            if course == 'cs2200' and not path:
                path = os.getenv('CORPUS_PATH')
            if course not in courses and path:
                try:
                    courses[course] = await asyncio.to_thread(Retriever, path, os.getenv('RETRIEVAL_MODE','lexical'))
                except Exception:
                    logger.error('Course %s could not be loaded; verify its private corpus configuration', course)
        try:
            if state['model'] is None and os.getenv('MODEL_BASE_URL') and os.getenv('MODEL_NAME'):
                state['model']=InferenceClient(os.environ['MODEL_BASE_URL'],os.environ['MODEL_NAME'],os.getenv('MODEL_API_KEY',''),provider=os.getenv('MODEL_PROVIDER','compatible'))
        except Exception:
            logger.error('Model could not be configured; verify model settings')
        yield
    app=FastAPI(title='Backbone API',lifespan=lifespan,docs_url=None,redoc_url=None)
    def configured(course): return course in courses and state['model'] is not None and (bool(token) or allow_unauthenticated)
    @app.get('/health')
    async def health(): return {'status':'ok'}
    @app.get('/ready')
    async def ready(course: Optional[CourseId] = None):
        available = [key for key in ('cs2110', 'cs2200') if configured(key)]
        if (course and course not in available) or not available:
            raise HTTPException(503,'Course corpus, model endpoint, and service authentication must be configured.')
        return {'status':'configured','courses':available,'note':'Configuration ready; provider reachability is verified when answering.'}
    @app.post('/api/chat')
    async def chat(body:ChatRequest,request:Request):
        if token and not hmac.compare_digest(request.headers.get('authorization',''),f'Bearer {token}'):
            raise HTTPException(401,'Service authentication required.')
        if not configured(body.course): raise HTTPException(503,f'{body.course.upper()} is not connected yet. Configure its course corpus, model endpoint, and service token.')
        now=time.monotonic()
        calls[:]=[t for t in calls if now-t<60]
        # Process-wide budget also caps spend behind a shared website proxy.
        if len(calls)>=rate_limit: raise HTTPException(429,'Backbone is busy. Please try again in a minute.',headers={'Retry-After':'60'})
        calls.append(now)
        try:
            chunks=await asyncio.to_thread(courses[body.course].search,body.query)
            if not chunks:
                return {'course':body.course,'answer':"I don't have enough relevant information in this course's available material to answer that. Try another question about this course.",'citations':[],'context':[]}
            answer=await state['model'].answer(body.query,chunks)
        except asyncio.CancelledError: raise
        except Exception as exc:
            import httpx
            if isinstance(exc,(httpx.TimeoutException,TimeoutError)): raise HTTPException(504,'The model took too long. Please try again.') from None
            logger.error('Retrieval or model request failed (%s)',type(exc).__name__)
            raise HTTPException(502,'The answer service is unavailable. Please try again shortly.') from None
        return {'course':body.course,'answer':answer,'citations':[{'source':c['source'],'details':c.get('details','')} for c in chunks],'context':chunks}
    return app

app=create_app()
