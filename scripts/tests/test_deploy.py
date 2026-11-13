import pytest
from scripts.deploy import wait_for_revision, validate_answer


def test_wait_ignores_old_revision_and_transient_failures():
    replies = iter([OSError('cold start'), {'commit': 'old'}, {'commit': 'new', 'instance': 'replacement'}])
    def request(url):
        result = next(replies)
        if isinstance(result, Exception): raise result
        return result
    wait_for_revision('https://api.example', 'new', request=request, sleep=lambda _: None, attempts=3)


def test_wait_fails_when_revision_never_arrives():
    with pytest.raises(RuntimeError, match='tested commit'):
        wait_for_revision('https://api.example', 'new', request=lambda _: {'commit': 'old'}, sleep=lambda _: None, attempts=2)


def test_live_answers_require_course_context_and_sources():
    good = {'course': 'cs2110', 'supports_history': True, 'answer': 'The bus carries one value. [1]', 'citations': [{'source':'notes'}], 'context': [{'text':'excerpt'}]}
    validate_answer(good, 'cs2110')
    for bad in [{**good, 'course':'cs2200'}, {**good, 'citations':[]}, {**good, 'answer':''}, {**good, 'supports_history': False}]:
        with pytest.raises(ValueError): validate_answer(bad, 'cs2110')


def test_same_commit_requires_a_replacement_instance():
    replies = iter([{'commit':'new', 'instance':'before'}, {'commit':'old', 'instance':'after'}, {'commit':'new'}, {'commit':'new','instance':'after'}])
    wait_for_revision('https://api.example', 'new', previous_instance='before', request=lambda _: next(replies), sleep=lambda _: None, attempts=4)


def test_matching_commit_on_same_instance_cannot_pass():
    with pytest.raises(RuntimeError):
        wait_for_revision('https://api.example', 'new', previous_instance='before', request=lambda _: {'commit':'new','instance':'before'}, sleep=lambda _: None, attempts=2)


def test_first_upgrade_requires_a_nonempty_instance():
    replies = iter([{'commit':'new'}, {'commit':'new', 'instance':'first'}])
    wait_for_revision('https://api.example', 'new', previous_instance=None, request=lambda _: next(replies), sleep=lambda _: None, attempts=2)


def test_homepage_check_identifies_the_workflow(monkeypatch):
    from scripts import deploy
    class Homepage:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'<title>Backbone</title>'
    def open_homepage(request, **kwargs):
        assert request.get_header('User-agent') == 'Backbone-GitHub-Actions'
        return Homepage()
    monkeypatch.setattr(deploy, 'urlopen', open_homepage)
    monkeypatch.setattr(deploy, 'wait_ready', lambda _: None)
    monkeypatch.setattr(deploy, 'request_json', lambda url,data: {'course':data['course'], 'supports_history':True, 'answer':'answer [1]', 'citations':[{}], 'context':[{}]})
    deploy.smoke('https://example.com')


def test_vercel_backend_verification_checks_revision_and_both_courses():
    from scripts.deploy import verify_backend
    def request(url):
        return {'commit':'new','instance':'dpl_ready'} if url.endswith('/health') else {'courses':['cs2110','cs2200']}
    verify_backend('https://api.example','new',request=request,sleep=lambda _:None,attempts=1)


def test_vercel_backend_verification_rejects_missing_course():
    from scripts.deploy import verify_backend
    def request(url):
        return {'commit':'new','instance':'dpl_ready'} if url.endswith('/health') else {'courses':['cs2200']}
    with pytest.raises(RuntimeError,match='course'):
        verify_backend('https://api.example','new',request=request,sleep=lambda _:None,attempts=1)
