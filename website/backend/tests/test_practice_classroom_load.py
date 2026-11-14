from website.backend.tools.evaluate_classroom import run_classroom

def test_thirty_students_reconnect_duplicate_submissions_and_teacher_polling(practice_database_url,monkeypatch):
    monkeypatch.setenv('PRACTICE_OWNER_TOKEN','test-classroom-only')
    report=run_classroom(practice_database_url)
    assert report['students']==30 and report['duplicate_http_deliveries']==120
    assert report['http_statuses'].get(500,0)==0
