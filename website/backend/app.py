import asyncio
import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from .inference import InferenceClient
from .retrieval import Retriever

logger=logging.getLogger(__name__)
class ChatRequest(BaseModel):
    query: str = Field(min_length=1,max_length=2000)
    @field_validator('query')
    @classmethod
    def nonblank(cls,value):
        if not value.strip(): raise ValueError('Enter a question')
        return value.strip()

def create_app(retriever=None, model=None, service_token=None, rate_limit=10, allow_unauthenticated=False):
    state={'retriever':retriever,'model':model,'error':None}
    token=service_token if service_token is not None else os.getenv('BACKEND_TOKEN','')
    calls=[]
    @asynccontextmanager
    async def lifespan(app):
        try:
            if state['retriever'] is None and os.getenv('CORPUS_PATH'):
                state['retriever']=await asyncio.to_thread(Retriever,os.environ['CORPUS_PATH'],os.getenv('RETRIEVAL_MODE','lexical'))
            if state['model'] is None and os.getenv('MODEL_BASE_URL') and os.getenv('MODEL_NAME'):
                state['model']=InferenceClient(os.environ['MODEL_BASE_URL'],os.environ['MODEL_NAME'],os.getenv('MODEL_API_KEY',''),provider=os.getenv('MODEL_PROVIDER','compatible'))
        except Exception:
            state['error']='Resources could not be loaded'
            logger.error('Backend resources could not be loaded; verify private corpus and retrieval configuration')
        yield
    app=FastAPI(title='Backbone API',lifespan=lifespan,docs_url=None,redoc_url=None)
    def configured(): return state['retriever'] is not None and state['model'] is not None and not state['error'] and (bool(token) or allow_unauthenticated)
    @app.get('/health')
    async def health(): return {'status':'ok'}
    @app.get('/ready')
    async def ready():
        if not configured(): raise HTTPException(503,'Course corpus, model endpoint, and service authentication must be configured.')
        return {'status':'configured','note':'Configuration ready; provider reachability is verified when answering.'}
    @app.post('/api/chat')
    async def chat(body:ChatRequest,request:Request):
        if token and not hmac.compare_digest(request.headers.get('authorization',''),f'Bearer {token}'):
            raise HTTPException(401,'Service authentication required.')
        if not configured(): raise HTTPException(503,'Backbone is not connected yet. Configure the course corpus, model endpoint, and service token.')
        now=time.monotonic()
        calls[:]=[t for t in calls if now-t<60]
        # Process-wide budget also caps spend behind a shared website proxy.
        if len(calls)>=rate_limit: raise HTTPException(429,'Backbone is busy. Please try again in a minute.',headers={'Retry-After':'60'})
        calls.append(now)
        try:
            chunks=await asyncio.to_thread(state['retriever'].search,body.query)
            if not chunks:
                return {'answer':"I don't have enough relevant information in the available notes to answer that. Try a question about pipelining, caches, or virtual memory.",'citations':[],'context':[]}
            answer=await state['model'].answer(body.query,chunks)
        except asyncio.CancelledError: raise
        except Exception as exc:
            import httpx
            if isinstance(exc,(httpx.TimeoutException,TimeoutError)): raise HTTPException(504,'The model took too long. Please try again.') from None
            logger.error('Retrieval or model request failed (%s)',type(exc).__name__)
            raise HTTPException(502,'The answer service is unavailable. Please try again shortly.') from None
        return {'answer':answer,'citations':[{'source':c['source'],'details':c.get('details','')} for c in chunks],'context':chunks}
    return app

app=create_app()
