"""Conservative attribution from persisted assistance, never from client flags."""
def conceptual_help(result):
    return bool(result.get('misconception')) or (
        result.get('status')=='incorrect' and result.get('reasoning_status')=='incorrect'
        and any(c.get('status')=='contradicted' and c.get('evidence') for c in result.get('criteria',[])))


def resolve_outcome(db, session_id, exercise_id):
    p=db.execute('SELECT * FROM practice_progress WHERE session_id=%s AND exercise_id=%s',(session_id,exercise_id)).fetchone()
    if not p or not p['completed'] or p['outcome'] not in (None,'pending_assistance'):return None
    helped=db.execute('SELECT 1 FROM practice_assistance WHERE session_id=%s AND exercise_id=%s AND at<=%s',(session_id,exercise_id,p['completed_at'])).fetchone()
    # A help request in flight when the answer was checked cannot prove independence.
    pending=db.execute("SELECT 1 FROM practice_submissions WHERE session_id=%s AND exercise_id=%s AND kind='hint' AND result IS NULL AND created_at<=%s",(session_id,exercise_id,p['completed_at'])).fetchone()
    outcome='corrected_with_help' if helped else 'pending_assistance' if pending else 'solved_independently'
    db.execute('UPDATE practice_progress SET outcome=%s WHERE session_id=%s AND exercise_id=%s',(outcome,session_id,exercise_id))
    return outcome if outcome!='pending_assistance' else None
