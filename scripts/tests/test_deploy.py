import pytest
from scripts.deploy import wait_for_revision, validate_answer, deploy_hook_url


def test_wait_ignores_old_revision_and_transient_failures():
    replies = iter([OSError('cold start'), {'commit': 'old'}, {'commit': 'new'}])
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


def test_hook_targets_exact_commit_and_rejects_other_hosts():
    assert deploy_hook_url('https://api.render.com/deploy/srv-example?key=private', 'a'*40).endswith('&ref='+'a'*40)
    with pytest.raises(ValueError): deploy_hook_url('https://evil.example/deploy?key=x', 'a'*40)
