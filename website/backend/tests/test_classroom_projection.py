from contextlib import contextmanager
import pytest
from website.backend.practice.bank import load_bank
from website.backend.practice.store import Store

@pytest.fixture
def store(practice_database_url):
 s=Store(practice_database_url);s.migrate();s.seed(load_bank());return s

def queries(store):
 original=store.connect;calls=[]
 class Count:
  def __init__(self,db):self.db=db
  def execute(self,*args,**kwargs):calls.append(args[0]);return self.db.execute(*args,**kwargs)
 @contextmanager
 def counted():
  with original() as db:yield Count(db)
 store.connect=counted
 try:rows=store.classroom()
 finally:store.connect=original
 return len(calls),rows

def test_classroom_round_trips_are_bounded_for_one_and_thirty_students(store):
 store.create_student('First');one,rows=queries(store)
 assert rows[0]['parent_outcome'] is None
 for i in range(29):store.create_student('Student '+str(i))
 thirty,rows=queries(store)
 assert len(rows)==30
 assert one==thirty and thirty<=4,{'one':one,'thirty':thirty}

def test_historical_bank_version_and_expired_outcome_remain_visible(store):
 t=store.create_student('Historical');store.select_exercise(t,'mem-03')
 a=store.begin_action(t,'mem-03','hint','pending-help',{'answer':'','work':''})
 c=store.begin_action(t,'mem-03','check','correct-work',{'answer':'2048 bytes','work':''})
 store.finish_action(t,c['id'],{'status':'correct'})
 with store.connect() as db:
  db.execute("UPDATE practice_submissions SET created_at=now()-interval '2 minutes' WHERE id=%s",(a['id'],))
  db.execute("INSERT INTO practice_exercises SELECT 'old-bank',id,definition FROM practice_exercises")
  db.execute("UPDATE practice_sessions SET bank_version='old-bank'")
 row=store.classroom()[0]
 assert row['display_name']=='Historical' and row['parent_outcome']=='solved_independently'
 assert row['hints_used']==0 and row['current_exercise']=='mem-03'
