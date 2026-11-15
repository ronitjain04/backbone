import json
import pytest
from scripts.release import release,ReleaseError,candidate_url,verify_target,Reply

SHA='a'*40
class Ops:
 def __init__(self,fail=None,stale=False):self.calls=[];self.fail=fail;self.stale=stale;self.reads=0
 def previous(self,site):return 'dpl_previous'
 def current_main(self):
  self.reads+=1;return 'b'*40 if self.stale and self.reads>1 else SHA
 def deploy(self,commit):self.calls.append('deploy');return 'https://backbone-candidate.vercel.app'
 def verify_candidate(self,url,commit):
  self.calls.append('verify')
  if self.fail=='candidate':raise ReleaseError('Candidate unavailable')
 def promote(self,url):self.calls.append('promote')
 def verify_alias(self,url,commit):
  self.calls.append('alias')
  if self.fail=='alias':raise ReleaseError('Alias unavailable')

def test_failed_candidate_and_stale_main_never_promote():
 for ops in (Ops(fail='candidate'),Ops(stale=True)):
  with pytest.raises(ReleaseError):release(SHA,'https://backbone-study.vercel.app',ops)
  assert 'promote' not in ops.calls

def test_validated_candidate_promotes_once_and_records_previous_release():
 ops=Ops();result=release(SHA,'https://backbone-study.vercel.app',ops)
 assert ops.calls==['deploy','verify','promote','alias']
 assert result['previous']=='dpl_previous' and result['commit']==SHA

def test_failed_alias_reports_code_recovery_without_database_rollback():
 ops=Ops(fail='alias')
 with pytest.raises(ReleaseError,match='vercel promote dpl_previous') as error:release(SHA,'https://backbone-study.vercel.app',ops)
 assert 'database' in str(error.value).lower() and ops.calls.count('promote')==1

@pytest.mark.parametrize('bad',['https://evil.example','https://secret@backbone.vercel.app','http://backbone.vercel.app','https://backbone.vercel.app?token=secret','https://backbone.vercel.app/path'])
def test_untrusted_deployment_output_cannot_become_a_candidate(bad):
 with pytest.raises(ReleaseError):candidate_url(json.dumps({'status':'ok','deployment':{'url':bad}}))

def test_machine_deployment_output_and_plain_cli_url_are_supported():
 url='https://backbone-candidate.vercel.app'
 assert candidate_url(json.dumps({'status':'ok','deployment':{'url':url}}))==url
 assert candidate_url(url+'\n')==url

class Transport:
 def __init__(self):self.calls=[];self.created=False
 def request(self,path,data=None):
  self.calls.append((path,data))
  if path=='/health':return Reply(200,{'commit':SHA,'instance':'dpl_candidate'})
  if path=='/ready':return Reply(200,{'courses':['cs2110','cs2200']})
  if path=='/api/practice/start':self.created=True;return Reply(200,{'session_id':'synthetic'})
  if path=='/api/practice/draft':return Reply(200,{'revision':1})
  if path=='/api/practice/state':return Reply(200,{'progress':{'num-01':{'answer':'45','completed':True}}})
  if path=='/api/practice/check':return Reply(200,{'status':'correct','sources':[{'source':'synthetic'}]})
  if path=='/api/practice/events':return Reply(200,{'events':[{'seq':1,'kind':'check_requested'}]})
  if path=='/api/practice/classroom':return Reply(401,{'detail':'Owner access required'})
  if path=='/api/practice/delete':return Reply(200,{'deleted':True})
  raise AssertionError(path)

def test_candidate_smoke_checks_saved_work_duplicate_replay_and_owner_boundary():
 transport=Transport();verify_target(transport,SHA,practice=True)
 checks=[b for p,b in transport.calls if p.endswith('/check')]
 assert len(checks)==2 and checks[0]==checks[1]
 assert transport.calls[-1][0].endswith('/delete')

def test_failed_practice_smoke_still_deletes_only_its_new_session():
 class Broken(Transport):
  def request(self,path,data=None):
   if path=='/api/practice/check':return Reply(503,{})
   return super().request(path,data)
 t=Broken()
 with pytest.raises(ReleaseError):verify_target(t,SHA,practice=True)
 assert t.created and t.calls[-1][0].endswith('/delete')

def test_failed_start_does_not_attempt_to_delete_an_existing_or_unknown_session():
 class NoStart(Transport):
  def request(self,path,data=None):
   if path=='/api/practice/start':return Reply(503,{})
   return super().request(path,data)
 t=NoStart()
 with pytest.raises(ReleaseError):verify_target(t,SHA,practice=True)
 assert not any(p.endswith('/delete') for p,_ in t.calls)


def test_command_errors_are_sanitized(monkeypatch):
 import subprocess
 from scripts import release as module
 def run(*a,**kw):raise subprocess.CalledProcessError(1,['secret-token'],stderr='private response')
 monkeypatch.setattr(module.subprocess,'run',run)
 with pytest.raises(ReleaseError) as err:module.run_cli(['vercel','curl'])
 assert 'secret' not in str(err.value) and 'private response' not in str(err.value)

@pytest.mark.parametrize('bad',['https://backbone\n.vercel.app','https://[invalid'])
def test_control_characters_and_malformed_urls_fail_with_controlled_error(bad):
 with pytest.raises(ReleaseError):candidate_url(json.dumps({'status':'ok','deployment':{'url':bad}}))


def test_candidate_assets_require_real_html_and_nonempty_javascript():
 from scripts.release import verify_assets
 class Assets:
  broken=False
  def request(self,path,data=None):
   if path=='/':return Reply(200,{},'<title>Backbone</title>')
   if path.endswith('.html'):return Reply(200,{},'<script src="/'+path.removeprefix('/').replace('.html','.js')+'"></script>')
   return Reply(200,{},'<html>fallback</html>' if self.broken else 'console.log("bundle")')
 a=Assets();verify_assets(a)
 a.broken=True
 with pytest.raises(ReleaseError):verify_assets(a)
