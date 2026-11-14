"""Cookie-authorized practice API on the same origin as the workspace."""
import asyncio
import hmac
import logging
import os
from uuid import UUID
import psycopg
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from .store import Store, Unauthorized, Conflict, RateLimited
from .checking import check as deterministic_check, verdict
from .assessment import assess, first_arithmetic_error
from .hints import make_hint, grounded_chunks

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
        except RateLimited as exc:raise HTTPException(429,str(exc),headers={'Retry-After':'60'}) from None
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

    @router.post('/select')
    async def select(body:Draft,request:Request):
        return await db('select_exercise',token(request),body.exercise_id)

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
        attempts=await db('attempts',student,body.exercise_id)
        current=resources()
        retriever=current.get('retrievers',{}).get('cs2110')
        try:
            if kind=='hint':
                result=await asyncio.to_thread(make_hint,exercise,reserved['hint_level'],attempts,retriever)
            else:
                result=await asyncio.to_thread(deterministic_check,exercise,body.answer,body.work)
                chunks=await asyncio.to_thread(grounded_chunks,exercise,retriever,body.work[:1500])
                arithmetic=first_arithmetic_error(body.work,width=16 if exercise['topic']=='lc3' else exercise['checker'].get('bits') or exercise['checker'].get('arithmetic_width'))
                if arithmetic:
                    result=verdict('incorrect','The first arithmetic equality we can verify as incorrect is quoted below. Recalculate that step before continuing.',
                                   misconception=arithmetic,reasoning_status='incorrect',value_status=result['status'],sources=chunks)
                elif result.get('requires_rubric') or (exercise['checker'].get('requires_reasoning') and not body.work.strip()) or (body.work.strip() and result['status']!='needs_clarification'):
                    reasoning=await assess(exercise,body.answer,body.work,chunks,current.get('model'),attempts)
                    if exercise['checker']['kind']=='explanation':result=reasoning
                    else:
                        value_status=result['status']
                        if value_status=='incorrect':
                            reasoning['status']='incorrect'
                            reasoning['message']='The final result still needs revision. '+reasoning['message']
                        elif reasoning['status']=='unavailable':
                            reasoning['status']='needs_clarification'
                            reasoning['message']='The final value checks out, but I could not assess the reasoning right now. Your work is saved.'
                        result=dict(reasoning,value_status=value_status,reasoning_status=reasoning.get('status'))
                elif not body.work.strip():
                    result['reasoning_status']='not_assessed'
                    if result['status']=='incorrect':result['clarification']='Could you show one intermediate step so we can identify a supported error?'
                result.setdefault('sources',[])
                if not result['sources']:result['sources']=chunks
        except Exception:
            logger.warning('Practice action could not be assessed')
            result=verdict('unavailable','The tutor is temporarily unavailable. Your attempted work is saved; retry later.')
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
