from fastapi.testclient import TestClient
from scripts.release import Reply,verify_target,verify_assets
from tests.browser.support.server import create_fixture_app
from website.backend.practice.store import Store

def test_release_smoke_uses_real_authorized_api_and_cleans_its_session(practice_database_url,monkeypatch,tmp_path):
 sha='a'*40;monkeypatch.setenv('BACKBONE_COMMIT',sha);monkeypatch.setenv('VERCEL_DEPLOYMENT_ID','dpl_fixture')
 # Backend tests are self-contained in a clean checkout; Chromium separately
 # validates the exact uploaded frontend artifact.
 (tmp_path/'index.html').write_text('<title>Backbone</title>')
 for name in ('practice','teacher'):
  (tmp_path/(name+'.html')).write_text('<script src="/'+name+'.js"></script>')
 for name in ('app','practice','teacher'):(tmp_path/(name+'.js')).write_text('console.log("synthetic");')
 with TestClient(create_fixture_app(practice_database_url,public_dir=tmp_path)) as client:
  class Transport:
   def request(self,path,data=None):
    r=client.request('GET' if data is None else 'POST',path,json=data,headers={'Origin':'http://testserver'})
    try:body=r.json()
    except ValueError:body={}
    return Reply(r.status_code,body,r.text)
  verify_assets(Transport())
  verify_target(Transport(),sha,practice=True)
 with Store(practice_database_url).connect() as db:
  assert db.execute('SELECT count(*) AS n FROM practice_students').fetchone()['n']==0
