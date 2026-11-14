"""Cookie-authorized practice API on the same origin as the workspace."""
import asyncio
import hmac
import logging
import os
from functools import partial
from uuid import UUID
import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from .store import Store, Unauthorized, Conflict

COOKIE='backbone_student'
logger=logging.getLogger(__name__)
class Start(BaseModel):
    name: str = Field(default='Student',max_length=60)
class Draft(BaseModel):
    exercise_id: str = Field(min_length=1,max_length=40,pattern=r'^[a-z0-9-]+$')
    answer: str = Field(default='',max_length=4000)
    work: str = Field(default='',max_length=6000)
    revision: int = Field(default=0,ge=0)
class Action(Draft):
    request_key: str = Field(min_length=8,max_length=100,pattern=r'^[a-zA-Z0-9-]+$')


def create_router(store=None, resources=lambda:{}):
    router=APIRouter(prefix='/api/practice')
    store=store or (Store(os.environ['DATABASE_URL']) if os.getenv('DATABASE_URL') else None)

    async def db(method,*args):
        if store is None:raise HTTPException(503,'Practice needs a PostgreSQL connection. Your existing study chat is still available.')
        try:return await asyncio.to_thread(getattr(store,method),*args)
        except Unauthorized as exc:raise HTTPException(401,str(exc)) from None
        except Conflict as exc:raise HTTPException(409,str(exc)) from None
        except KeyError:raise HTTPException(404,'Exercise not found.') from None
        except psycopg.Error:
            logger.warning('Practice database operation failed')
            raise HTTPException(503,'Saved practice is temporarily unavailable. Keep your work and retry.') from None

    def token(request):return request.cookies.get(COOKIE,'')
    def owner(request):
        configured=os.getenv('PRACTICE_OWNER_TOKEN','')
        if not configured or not hmac.compare_digest(request.headers.get('x-practice-owner',''),configured):
            raise HTTPException(401,'Owner access required.')

    @router.post('/start')
    async def start(body:Start,request:Request,response:Response):
        existing=token(request)
        if existing:
            try:return await db('snapshot',existing)
            except HTTPException as exc:
                if exc.status_code!=401:raise
        session_token=await db('create_student',body.name.strip())
        response.set_cookie(COOKIE,session_token,max_age=30*86400,httponly=True,samesite='strict',secure=request.url.scheme=='https',path='/api/practice')
        return await db('snapshot',session_token)

    @router.get('/state')
    async def state(request:Request):return await db('snapshot',token(request))

    @router.post('/draft')
    async def draft(body:Draft,request:Request):
        return await db('save_draft',token(request),body.exercise_id,body.answer,body.work,body.revision)

    async def action(kind,body,request):
        student=token(request)
        exercise=await db('exercise',student,body.exercise_id)
        content={'answer':body.answer,'work':body.work}
        # The action itself durably records all work, even if a draft save was interrupted.
        reserved=await db('begin_action',student,body.exercise_id,kind,body.request_key,content)
        if not reserved['new']:
            if reserved['result'] is not None:return reserved['result']
            raise HTTPException(409,'This request is still processing. Your work is saved; retry shortly.')
        result={'status':'unavailable','message':'The tutor is not configured yet. Your attempted work is saved.','misconception':None,'sources':[]}
        return await db('finish_action',student,reserved['id'],result)

    @router.post('/check')
    async def check(body:Action,request:Request):return await action('check',body,request)

    @router.post('/hint')
    async def hint(body:Action,request:Request):return await action('hint',body,request)

    @router.get('/events')
    async def events(request:Request):return {'events':await db('events',token(request))}

    @router.get('/classroom')
    async def classroom(request:Request):
        owner(request);return {'sessions':await db('classroom')}

    @router.get('/classroom/{session_id}/events')
    async def classroom_events(session_id:UUID,request:Request):
        owner(request);return {'events':await db('classroom_events',str(session_id))}

    @router.post('/delete')
    async def delete(request:Request,response:Response):
        await db('delete',token(request));response.delete_cookie(COOKIE,path='/api/practice')
        return {'deleted':True}

    return router
