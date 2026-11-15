"""Compact teacher projections, connection signals, and persisted visual interactions."""
from datetime import datetime, timezone
from uuid import UUID
from psycopg.types.json import Jsonb
from .visual import SUPPORTED
from .errors import Conflict, RateLimited

CONCEPTS={'mem-01':'address-count','mem-02':'address-count','mem-03':'capacity','mem-04':'capacity-units','mem-05':'capacity','mem-06':'addressability','num-01':'place-value','num-02':'signed-decoding','num-03':'negation','num-04':'signed-range','num-05':'overflow','num-06':'bitwise-mask','lc3-01':'register-arithmetic','lc3-02':'register-not','lc3-03':'condition-codes','lc3-04':'pc-relative','lc3-05':'register-program','lc3-06':'load-address'}


def presence_label(age,connected):
    if not connected or age is None or age>120:return 'disconnected'
    return 'active' if age<45 else 'stale'


class ClassroomStore:
    def presence(self,token,tab_id,sequence,connected):
        with self.connect() as db:
            s=self.session(db,token,True)
            old=db.execute('SELECT * FROM practice_presence WHERE session_id=%s AND tab_id=%s',(s['id'],UUID(tab_id))).fetchone()
            if old and sequence<=old['sequence']:return {'accepted':False}
            # Bound abandoned tabs without growing indefinitely; old signals already mean disconnected.
            db.execute("DELETE FROM practice_presence WHERE session_id=%s AND seen_at<now()-interval '1 day'",(s['id'],))
            if not old and db.execute('SELECT count(*) AS n FROM practice_presence WHERE session_id=%s',(s['id'],)).fetchone()['n']>=20:
                raise RateLimited('Too many active browser tabs for this session.')
            db.execute('INSERT INTO practice_presence(session_id,tab_id,sequence,connected) VALUES (%s,%s,%s,%s) ON CONFLICT(session_id,tab_id) DO UPDATE SET sequence=EXCLUDED.sequence,connected=EXCLUDED.connected,seen_at=clock_timestamp()', (s['id'],UUID(tab_id),sequence,connected))
            if not old or old['connected']!=connected or (connected and (datetime.now(timezone.utc)-old['seen_at']).total_seconds()>45):
                self.event(db,s,'presence_changed',payload={'tab_id':tab_id,'connected':connected})
        return {'accepted':True}

    def visual_retry(self,token,exercise_id,key,content):
        with self.connect() as db:
            s=self.session(db,token)
            existing=db.execute('SELECT input,result FROM practice_interactions WHERE session_id=%s AND request_key=%s',(s['id'],key)).fetchone()
            if not existing:return None
            if existing['input']!={'exercise_id':exercise_id,**content}:raise Conflict('This request ID was already used with different visual settings.')
            return existing['result']

    def visual(self,token,exercise_id,key,content,result):
        if exercise_id not in SUPPORTED:raise KeyError('No visual')
        with self.connect() as db:
            s=self.session(db,token,True);self.ensure_progress(db,s,exercise_id)
            existing=db.execute('SELECT * FROM practice_interactions WHERE session_id=%s AND request_key=%s',(s['id'],key)).fetchone()
            bound={'exercise_id':exercise_id,**content}
            if existing:
                if existing['input']!=bound:raise Conflict('This request ID was already used with different visual settings.')
                return existing['result']
            self.budget(db,'visual','minute',180)
            prior=db.execute('SELECT 1 FROM practice_visuals WHERE session_id=%s AND exercise_id=%s',(s['id'],exercise_id)).fetchone()
            db.execute('INSERT INTO practice_visuals VALUES (%s,%s,%s,%s,%s) ON CONFLICT(session_id,exercise_id) DO UPDATE SET stage=EXCLUDED.stage,address_bits=EXCLUDED.address_bits,bits_per_location=EXCLUDED.bits_per_location',(s['id'],exercise_id,content['stage'],content['address_bits'],content['bits_per_location']))
            db.execute('INSERT INTO practice_assistance(session_id,exercise_id,source_key,kind) VALUES (%s,%s,%s,%s)',(s['id'],exercise_id,'visual:'+key,'visual'))
            result={**result,**content}
            db.execute('INSERT INTO practice_interactions VALUES (%s,%s,%s,%s)',(s['id'],key,Jsonb(bound),Jsonb(result)))
            self.event(db,s,'visual_changed' if prior else 'visual_opened',exercise_id,result)
        return result

    def classroom(self):
        with self.connect() as db:
            # Recover only expired actions for the displayed classroom, acquiring locks
            # in UUID order so concurrent teacher reads cannot invert session locks.
            expired=db.execute("""SELECT DISTINCT session_id FROM practice_submissions
                WHERE result IS NULL AND created_at<clock_timestamp()-interval '90 seconds'
                AND session_id IN (SELECT id FROM practice_sessions ORDER BY created_at DESC LIMIT 100)
                ORDER BY session_id""").fetchall()
            for item in expired:
                session=db.execute('SELECT id FROM practice_sessions WHERE id=%s FOR UPDATE',(item['session_id'],)).fetchone()
                if session is not None:self.expire_actions(db,session)
            rows=db.execute("""WITH students AS (
                SELECT s.id,s.bank_version,s.selected_exercise,s.created_at,st.display_name
                FROM practice_sessions s JOIN practice_students st ON st.id=s.student_id
                ORDER BY s.created_at DESC LIMIT 100
            ) SELECT s.*,x.definition,
                (SELECT max(at) FROM practice_events e WHERE e.session_id=s.id AND e.kind!='presence_changed') AS last_activity,
                (SELECT max(seen_at) FROM practice_presence p WHERE p.session_id=s.id AND p.connected) AS last_signal,
                (SELECT max(seen_at) FROM practice_presence p WHERE p.session_id=s.id) AS any_signal,
                COALESCE(p.completed,0) AS completed, COALESCE(p.progress,'[]'::jsonb) AS progress,
                a.id AS action_id,a.input AS latest_input,a.result AS latest_result,a.created_at AS latest_at,
                (SELECT count(*) FROM practice_hints h JOIN practice_submissions sub ON sub.id=h.submission_id WHERE sub.session_id=s.id) AS hints_used
                FROM students s JOIN practice_exercises x ON x.version=s.bank_version AND x.id=s.selected_exercise
                LEFT JOIN LATERAL (
                    SELECT count(*) FILTER (WHERE completed) AS completed,
                    jsonb_agg(jsonb_build_object('exercise_id',exercise_id,'outcome',outcome)) AS progress
                    FROM practice_progress WHERE session_id=s.id
                ) p ON true
                LEFT JOIN LATERAL (
                    SELECT id,input,result,created_at FROM practice_submissions
                    WHERE session_id=s.id AND exercise_id=s.selected_exercise AND kind='check' AND result IS NOT NULL
                    ORDER BY created_at DESC,id DESC LIMIT 1
                ) a ON true ORDER BY s.created_at DESC""").fetchall()
            results=[];now=datetime.now(timezone.utc)
            for s in rows:
                eid=s['selected_exercise'];definition=s['definition'];progress=s['progress']
                latest={'id':s['action_id'],'input':s['latest_input'],'result':s['latest_result'],'created_at':s['latest_at']} if s['action_id'] else None
                diagnosis=None;clarify=False
                if latest:
                    result=latest['result'];finding=result.get('misconception');text=latest['input'].get('work','')
                    if definition['checker']['kind']=='explanation':text=latest['input'].get('answer','')+'\n'+text
                    if result.get('status')=='incorrect' and finding and finding.get('evidence') and finding['evidence'] in text:
                        diagnosis={**finding,'action_id':str(latest['id']),'at':latest['created_at'].isoformat()}
                    clarify=result.get('status')=='needs_clarification' or bool(result.get('clarification')) and not diagnosis
                base=eid.removesuffix('-follow');ps={p['exercise_id']:p for p in progress}
                signal=s['last_signal'];age=(now-signal).total_seconds() if signal else None
                results.append({'id':str(s['id']),'display_name':s['display_name'],'created_at':s['created_at'].isoformat(),
                    'current_exercise':eid,'exercise_title':definition['title'],'topic':definition['topic'],
                    'last_activity':s['last_activity'].isoformat() if s['last_activity'] else None,
                    'last_signal':s['any_signal'].isoformat() if s['any_signal'] else None,'presence':presence_label(age,bool(signal)),
                    'completed':s['completed'],'hints_used':s['hints_used'],
                    'diagnosis':diagnosis,'clarification_needed':clarify,
                    'group_key':definition['topic']+':'+CONCEPTS.get(base,base)+':'+str(diagnosis.get('criterion','supported')) if diagnosis else 'clarification' if clarify else None,
                    'parent_outcome':ps.get(base,{}).get('outcome'),'follow_up_outcome':ps.get(base+'-follow',{}).get('outcome')})
            return results

    def classroom_detail(self,session_id):
        with self.connect() as db:
            attempts=db.execute('SELECT id,exercise_id,kind,input,result,created_at FROM practice_submissions WHERE session_id=%s AND result IS NOT NULL ORDER BY created_at,id',(UUID(session_id),)).fetchall()
            return {'attempts':[dict(a,id=str(a['id']),created_at=a['created_at'].isoformat()) for a in attempts]}
