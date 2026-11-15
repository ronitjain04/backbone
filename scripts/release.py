"""Stage, verify, then promote. No production domain changes occur during PR checks."""
from contextlib import contextmanager
from dataclasses import dataclass
import http.cookiejar
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.request import build_opener, HTTPCookieProcessor, Request
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]

class ReleaseError(RuntimeError):
    pass

@dataclass
class Reply:
    status: int
    body: dict
    text: str = ''


def validated_url(value):
    if not isinstance(value,str) or not re.fullmatch(r'https://[a-z0-9-]+\.vercel\.app/?',value):
        raise ReleaseError('Unexpected deployment URL; refusing to contact or promote it')
    return value.rstrip('/')


def candidate_url(output):
    try:
        data=json.loads(output)
        if data.get('status')!='ok':raise ReleaseError('Candidate creation did not succeed')
        return validated_url(data['deployment']['url'])
    except json.JSONDecodeError:
        return validated_url(output.strip())
    except (KeyError,TypeError,AttributeError):
        raise ReleaseError('Unrecognized deployment output') from None


def checked(transport,path,data=None):
    result=transport.request(path,data)
    if not 200<=result.status<300 or not isinstance(result.body,dict):
        raise ReleaseError('Verification endpoint failed: '+path)
    return result.body


def verify_assets(transport):
    for path,marker in (('/','Backbone'),('/practice.html','/practice.js'),('/teacher.html','/teacher.js')):
        reply=transport.request(path)
        if reply.status!=200 or marker not in reply.text:raise ReleaseError('Candidate HTML asset verification failed')
    for path in ('/app.js','/practice.js','/teacher.js'):
        reply=transport.request(path)
        if reply.status!=200 or not reply.text.strip() or reply.text.lstrip().startswith('<'):
            raise ReleaseError('Candidate JavaScript asset verification failed')


def verify_target(transport,commit,*,practice=False):
    health=checked(transport,'/health')
    if health.get('commit')!=commit or not health.get('instance'):
        raise ReleaseError('Deployment is not serving the tested commit')
    if not {'cs2110','cs2200'}.issubset(checked(transport,'/ready').get('courses',[])):
        raise ReleaseError('Deployment is missing a configured course')
    if not practice:return
    started=checked(transport,'/api/practice/start',{'name':'CI release verification'})
    if not started.get('session_id'):raise ReleaseError('Could not create the disposable practice session')
    try:
        checked(transport,'/api/practice/draft',{'exercise_id':'num-01','answer':'45','work':'','revision':0})
        state=checked(transport,'/api/practice/state')
        if state.get('progress',{}).get('num-01',{}).get('answer')!='45':raise ReleaseError('Practice draft did not persist')
        action={'exercise_id':'num-01','answer':'45','work':'','request_key':str(uuid4())}
        result=checked(transport,'/api/practice/check',action)
        if result.get('status')!='correct' or not result.get('sources'):raise ReleaseError('Deterministic practice or source verification failed')
        if checked(transport,'/api/practice/check',action)!=result:raise ReleaseError('Duplicate submission was not idempotent')
        state=checked(transport,'/api/practice/state')
        if not state.get('progress',{}).get('num-01',{}).get('completed'):raise ReleaseError('Practice completion did not persist')
        events=checked(transport,'/api/practice/events').get('events',[])
        if ([e.get('seq') for e in events]!=list(range(1,len(events)+1))
                or sum(e.get('kind')=='check_requested' for e in events)!=1):raise ReleaseError('Replay sequence or duplicate action count failed')
        if transport.request('/api/practice/classroom').status!=401:raise ReleaseError('Teacher boundary allowed a student session')
    finally:
        if checked(transport,'/api/practice/delete',{}).get('deleted') is not True:
            raise ReleaseError('Disposable verification session cleanup failed')


def release(commit,site_url,ops):
    if not re.fullmatch('[0-9a-f]{40}',commit):raise ReleaseError('Expected a full tested Git revision')
    site_url=validated_url(site_url)
    previous=ops.previous(site_url)
    if not re.fullmatch('dpl_[A-Za-z0-9]+',previous):raise ReleaseError('Cannot identify the previous deployment for code recovery')
    if ops.current_main()!=commit:raise ReleaseError('A newer main commit exists; refusing to release stale code')
    candidate=validated_url(ops.deploy(commit))
    ops.verify_candidate(candidate,commit)
    if ops.current_main()!=commit:raise ReleaseError('Main changed during candidate verification; candidate was not promoted')
    ops.promote(candidate)
    try:ops.verify_alias(site_url,commit)
    except Exception:
        raise ReleaseError('Public alias verification failed after promotion. Restore previous code with: vercel promote '+previous+'. Database rollback is not automatic; migrations must remain backward-compatible.') from None
    return {'commit':commit,'candidate':candidate,'previous':previous,'promoted':True}


def run_cli(args,*,cwd=ROOT):
    try:return subprocess.run(args,cwd=cwd,check=True,capture_output=True,text=True,timeout=600).stdout
    except (OSError,subprocess.SubprocessError):raise ReleaseError('Release command failed; inspect the protected deployment logs') from None


def parse_reply(raw,marker='\nBACKBONE_HTTP:'):
    try:
        body,status=raw.rsplit(marker,1)
        try:payload=json.loads(body)
        except ValueError:payload={}
        return Reply(int(status),payload,body)
    except (ValueError,TypeError):raise ReleaseError('Deployment returned an invalid verification response') from None


class CandidateTransport:
    def __init__(self,base,jar):self.base=validated_url(base);self.jar=jar
    def request(self,path,data=None):
        args=['vercel','curl',path,'--deployment',self.base,'--','--silent','--show-error','--max-time','80',
              '--write-out','\nBACKBONE_HTTP:%{http_code}','--cookie',self.jar,'--cookie-jar',self.jar,'--header','Origin: '+self.base]
        if data is not None:args+=['--request','POST','--header','Content-Type: application/json','--data',json.dumps(data)]
        return parse_reply(run_cli(args,cwd=ROOT/'website'))


class PublicTransport:
    def __init__(self,base):self.base=validated_url(base);self.opener=build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(self,path,data=None):
        payload=None if data is None else json.dumps(data).encode()
        req=Request(self.base+path,data=payload,headers={'Content-Type':'application/json','Origin':self.base,'User-Agent':'Backbone-GitHub-Actions'})
        try:
            with self.opener.open(req,timeout=80) as response:
                raw=response.read().decode('utf-8')
                return parse_reply(raw+'\nBACKBONE_HTTP:'+str(response.status))
        except HTTPError as error:
            try:body=json.load(error)
            except (ValueError,OSError):body={}
            return Reply(error.code,body)
        except (OSError,ValueError):raise ReleaseError('Public verification request failed') from None


class VercelOps:
    def previous(self,site):return checked(PublicTransport(site),'/health').get('instance','')
    def current_main(self):
        output=run_cli(['git','ls-remote','origin','refs/heads/main'])
        return output.split()[0] if output.split() else ''
    def deploy(self,commit):
        url=candidate_url(run_cli(['vercel','deploy','--prod','--skip-domain','--yes','--cwd','website','--env','BACKBONE_COMMIT='+commit]))
        write_summary('Candidate created, not promoted: '+url+' · tested commit `'+commit+'`.')
        return url
    @contextmanager
    def candidate(self,url):
        with tempfile.TemporaryDirectory(prefix='backbone-release-') as directory:
            jar=Path(directory)/'cookies';jar.touch(mode=0o600)
            yield CandidateTransport(url,str(jar))
    def verify_candidate(self,url,commit):
        with self.candidate(url) as transport:
            verify_assets(transport)
            verify_target(transport,commit,practice=True)
    def promote(self,url):run_cli(['vercel','promote',url,'--yes','--timeout','3m','--cwd','website'])
    def verify_alias(self,url,commit):verify_target(PublicTransport(url),commit)


def write_summary(text):
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as out:out.write(text+'\n\n')


def main():
    try:
        result=release(os.environ['GITHUB_SHA'],os.environ['SITE_URL'],VercelOps())
        summary='Verified and promoted commit `'+result['commit']+'`.\n\nCandidate: '+result['candidate']+'\n\nPrevious deployment: `'+result['previous']+'`. Code rollback does not roll back database migrations.\n'
        write_summary(summary)
        print(summary)
    except ReleaseError as error:
        # These messages are controlled here; raw CLI/HTTP exceptions never reach logs.
        write_summary('Release failed: '+str(error))
        print('Release failed: '+str(error))
        raise SystemExit(1) from None
    except Exception as error:
        message='Release failed ('+type(error).__name__+'); inspect protected deployment logs. No automatic database rollback was attempted.'
        write_summary(message);print(message)
        raise SystemExit(1) from None

if __name__=='__main__':main()
