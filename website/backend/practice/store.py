"""PostgreSQL persistence; every mutation owns the session lock and its events."""
import hashlib
import secrets
from pathlib import Path
from uuid import uuid4, UUID
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from .bank import BANK_VERSION, public_exercise

CLASSROOM = UUID('681f864f-13a5-439b-a1db-5cac9b9ecb73')
class Unauthorized(Exception): pass
class Conflict(Exception): pass


class Store:
    def __init__(self, dsn):
        self.dsn = dsn

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row, connect_timeout=5, options='-c statement_timeout=10000')

    def migrate(self):
        with self.connect() as db:
            db.execute('SELECT pg_advisory_xact_lock(211014)')
            db.execute(Path(__file__).with_name('migrations').joinpath('001_practice.sql').read_text())

    def seed(self, bank):
        with self.connect() as db:
            db.execute('INSERT INTO practice_classrooms VALUES (%s,%s) ON CONFLICT DO NOTHING', (CLASSROOM, 'CS 2110 · Guided practice'))
            for e in bank.values():
                for record in (e, e['follow_up']):
                    db.execute('INSERT INTO practice_exercises VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                               (record['version'],record['id'],Jsonb(record)))

    def session(self, db, token, lock=False):
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = db.execute('SELECT * FROM practice_sessions WHERE token_digest=%s' + (' FOR UPDATE' if lock else ''), (digest,)).fetchone()
        if not row: raise Unauthorized('Start a student session to continue.')
        return row

    def event(self, db, session, kind, exercise_id=None, payload=None):
        seq = db.execute('UPDATE practice_sessions SET next_seq=next_seq+1 WHERE id=%s RETURNING next_seq-1 AS seq', (session['id'],)).fetchone()['seq']
        db.execute('INSERT INTO practice_events(session_id,seq,kind,exercise_id,payload) VALUES (%s,%s,%s,%s,%s)',
                   (session['id'],seq,kind,exercise_id,Jsonb(payload or {})))

    def create_student(self, name='Student'):
        student, session, token = uuid4(), uuid4(), secrets.token_urlsafe(32)
        with self.connect() as db:
            db.execute('INSERT INTO practice_students(id,display_name) VALUES (%s,%s)', (student,name[:60] or 'Student'))
            db.execute('INSERT INTO practice_memberships VALUES (%s,%s)', (student,CLASSROOM))
            db.execute('INSERT INTO practice_sessions(id,student_id,classroom_id,token_digest,bank_version) VALUES (%s,%s,%s,%s,%s)',
                       (session,student,CLASSROOM,hashlib.sha256(token.encode()).hexdigest(),BANK_VERSION))
            self.event(db,{'id':session},'session_started')
        return token

    def exercise(self, token, exercise_id):
        with self.connect() as db:
            s=self.session(db,token)
            row=db.execute('SELECT definition FROM practice_exercises WHERE version=%s AND id=%s',(s['bank_version'],exercise_id)).fetchone()
            if not row: raise KeyError('Exercise not found')
            return row['definition']

    def snapshot(self, token):
        with self.connect() as db:
            s=self.session(db,token)
            exercises=db.execute('SELECT definition FROM practice_exercises WHERE version=%s ORDER BY id',(s['bank_version'],)).fetchall()
            progress=db.execute('SELECT exercise_id,answer,work,revision,completed,hint_level FROM practice_progress WHERE session_id=%s',(s['id'],)).fetchall()
            actions=db.execute('SELECT id,exercise_id,kind,result,created_at FROM practice_submissions WHERE session_id=%s ORDER BY created_at,id',(s['id'],)).fetchall()
            return {'session_id':str(s['id']),'classroom':'CS 2110 · Guided practice','exercises':[public_exercise(r['definition']) for r in exercises],
                    'progress':{r['exercise_id']:{k:v for k,v in r.items() if k!='exercise_id'} for r in progress},
                    'actions':[dict(r,id=str(r['id']),created_at=r['created_at'].isoformat()) for r in actions]}

    def ensure_progress(self, db, s, exercise_id):
        if not db.execute('SELECT 1 FROM practice_exercises WHERE version=%s AND id=%s',(s['bank_version'],exercise_id)).fetchone(): raise KeyError('Exercise not found')
        db.execute('INSERT INTO practice_progress(session_id,exercise_id) VALUES (%s,%s) ON CONFLICT DO NOTHING',(s['id'],exercise_id))

    def save_draft(self, token, exercise_id, answer, work, revision):
        with self.connect() as db:
            s=self.session(db,token,True); self.ensure_progress(db,s,exercise_id)
            row=db.execute('UPDATE practice_progress SET answer=%s,work=%s,revision=revision+1,updated_at=clock_timestamp() WHERE session_id=%s AND exercise_id=%s AND revision=%s RETURNING revision',
                           (answer,work,s['id'],exercise_id,revision)).fetchone()
            if not row: raise Conflict('A newer draft exists. Reload to see the latest saved work.')
            self.event(db,s,'draft_saved',exercise_id,{'answer':answer,'work':work,'revision':row['revision']})
            return row

    def begin_action(self, token, exercise_id, kind, request_key, content):
        with self.connect() as db:
            s=self.session(db,token,True); self.ensure_progress(db,s,exercise_id)
            existing=db.execute('SELECT * FROM practice_submissions WHERE session_id=%s AND request_key=%s',(s['id'],request_key)).fetchone()
            if existing:
                if existing['exercise_id']!=exercise_id or existing['kind']!=kind or existing['input']!=content:
                    raise Conflict('This request ID was already used with different work.')
                return {'id':str(existing['id']),'result':existing['result'],'new':False,'hint_level':existing['hint_level']}
            # Recoverable timeouts do not permanently block new hint requests.
            if kind=='hint' and db.execute("SELECT 1 FROM practice_submissions WHERE session_id=%s AND exercise_id=%s AND kind='hint' AND result IS NULL AND created_at>now()-interval '90 seconds'",(s['id'],exercise_id)).fetchone():
                raise Conflict('A hint is already being prepared. Please wait a moment.')
            level=db.execute('SELECT hint_level FROM practice_progress WHERE session_id=%s AND exercise_id=%s',(s['id'],exercise_id)).fetchone()['hint_level']
            action=uuid4(); level=min(level+1,3) if kind=='hint' else None
            db.execute('INSERT INTO practice_submissions(id,session_id,exercise_id,request_key,kind,input,hint_level) VALUES (%s,%s,%s,%s,%s,%s,%s)',
                       (action,s['id'],exercise_id,request_key,kind,Jsonb(content),level))
            self.event(db,s,kind+'_requested',exercise_id,{'action_id':str(action),**content})
            return {'id':str(action),'new':True,'result':None,'hint_level':level}

    def finish_action(self, token, action_id, result):
        with self.connect() as db:
            s=self.session(db,token,True)
            action=db.execute('SELECT * FROM practice_submissions WHERE session_id=%s AND id=%s',(s['id'],UUID(str(action_id)))).fetchone()
            if not action: raise Unauthorized('Action not found')
            if action['result'] is not None: return action['result']
            db.execute('UPDATE practice_submissions SET result=%s WHERE id=%s',(Jsonb(result),action['id']))
            if action['kind']=='check':
                db.execute('INSERT INTO practice_feedback(submission_id,content) VALUES (%s,%s)',(action['id'],Jsonb(result)))
                if result['status']=='correct':
                    db.execute('UPDATE practice_progress SET completed=true WHERE session_id=%s AND exercise_id=%s',(s['id'],action['exercise_id']))
            elif result['status']=='hint':
                db.execute('INSERT INTO practice_hints VALUES (%s,%s,%s)',(action['id'],action['hint_level'],Jsonb(result)))
                db.execute('UPDATE practice_progress SET hint_level=GREATEST(hint_level,%s) WHERE session_id=%s AND exercise_id=%s',(action['hint_level'],s['id'],action['exercise_id']))
            self.event(db,s,action['kind']+'_finished',action['exercise_id'],{'action_id':str(action['id']),**result})
        return result

    def attempts(self, token, exercise_id):
        with self.connect() as db:
            s=self.session(db,token)
            return db.execute('SELECT kind,input,result,hint_level FROM practice_submissions WHERE session_id=%s AND exercise_id=%s ORDER BY created_at,id',(s['id'],exercise_id)).fetchall()

    def events(self, token):
        with self.connect() as db:
            s=self.session(db,token)
            return [dict(r,at=r['at'].isoformat()) for r in db.execute('SELECT seq,at,kind,exercise_id,payload FROM practice_events WHERE session_id=%s ORDER BY seq',(s['id'],))]

    def classroom(self):
        with self.connect() as db:
            rows=db.execute('SELECT s.id,st.display_name,s.created_at,count(p.exercise_id) FILTER (WHERE p.completed) AS completed FROM practice_sessions s JOIN practice_students st ON st.id=s.student_id LEFT JOIN practice_progress p ON p.session_id=s.id GROUP BY s.id,st.display_name ORDER BY s.created_at DESC LIMIT 100').fetchall()
            return [dict(r,id=str(r['id']),created_at=r['created_at'].isoformat()) for r in rows]

    def classroom_events(self, session_id):
        with self.connect() as db:
            return [dict(r,at=r['at'].isoformat()) for r in db.execute('SELECT seq,at,kind,exercise_id,payload FROM practice_events WHERE session_id=%s ORDER BY seq',(UUID(session_id),))]

    def delete(self, token):
        with self.connect() as db:
            s=self.session(db,token,True)
            db.execute('DELETE FROM practice_students WHERE id=%s',(s['student_id'],))
