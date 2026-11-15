"""Upgrade the populated pre-classroom schema, rather than only testing empty installs."""
from pathlib import Path
from uuid import uuid4
from psycopg.types.json import Jsonb
from website.backend.practice.store import Store
from website.backend.practice.bank import load_bank,BANK_VERSION

def test_populated_001_upgrades_without_losing_work_or_inventing_independence(practice_database_url):
 s=Store(practice_database_url);student,session,classroom=uuid4(),uuid4(),uuid4();e=load_bank()['num-01']
 with s.connect() as db:
  db.execute(Path('website/backend/practice/migrations/001_practice.sql').read_text())
  db.execute('INSERT INTO practice_classrooms VALUES (%s,%s)',(classroom,'Synthetic old classroom'))
  db.execute('INSERT INTO practice_students(id,display_name) VALUES (%s,%s)',(student,'Synthetic old student'))
  db.execute('INSERT INTO practice_memberships VALUES (%s,%s)',(student,classroom))
  db.execute('INSERT INTO practice_exercises VALUES (%s,%s,%s)',(BANK_VERSION,e['id'],Jsonb(e)))
  db.execute('INSERT INTO practice_sessions(id,student_id,classroom_id,token_digest,bank_version) VALUES (%s,%s,%s,%s,%s)',(session,student,classroom,'synthetic-digest',BANK_VERSION))
  db.execute("INSERT INTO practice_progress(session_id,exercise_id,answer,work,completed,hint_level,revision) VALUES (%s,'num-01','45','32+8+4+1',true,1,3)",(session,))
  db.execute("INSERT INTO practice_events(session_id,seq,kind,exercise_id,payload) VALUES (%s,1,'check_finished','num-01',%s)",(session,Jsonb({'status':'correct','message':'Recorded old feedback'})))
 s.migrate();s.migrate()
 with s.connect() as db:
  p=db.execute('SELECT * FROM practice_progress WHERE session_id=%s',(session,)).fetchone()
  assert (p['answer'],p['work'],p['revision'],p['hint_level'],p['outcome'])==('45','32+8+4+1',3,1,'historical_unclassified')
  assert db.execute('SELECT count(*) AS n FROM practice_events WHERE session_id=%s',(session,)).fetchone()['n']==1
  assert db.execute('SELECT count(*) AS n FROM practice_migrations').fetchone()['n']==2
