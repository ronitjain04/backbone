"""Deployment verification. Credentials are read only from the environment."""
import json
import os
import sys
import time
from urllib.request import Request, urlopen


def request_json(url, data=None):
    body = None if data is None else json.dumps(data).encode()
    headers = {'Content-Type': 'application/json', 'User-Agent': 'Backbone-GitHub-Actions'}
    with urlopen(Request(url, data=body, headers=headers), timeout=80) as response:
        return json.load(response)


def wait_for_revision(base, commit, *, request=request_json, sleep=time.sleep, attempts=90, previous_instance=None):
    for attempt in range(attempts):
        try:
            health = request(base.rstrip('/') + '/health')
            if health.get('commit') == commit and health.get('instance') and health['instance'] != previous_instance:
                return
        except (OSError, ValueError):
            pass
        if attempt + 1 < attempts:
            sleep(10)
    raise RuntimeError('Backend did not serve the tested commit before the deployment deadline')


def wait_ready(base, *, request=request_json, sleep=time.sleep, attempts=30):
    for attempt in range(attempts):
        try:
            if all(request(base.rstrip('/') + '/api/status?course=' + course).get('ready') is True
                   for course in ('cs2110', 'cs2200')):
                return
        except (OSError, ValueError):
            pass
        if attempt + 1 < attempts:
            sleep(10)
    raise RuntimeError('The public site did not report both courses ready')


def validate_answer(data, course):
    if (data.get('course') != course or data.get('supports_history') is not True
            or not isinstance(data.get('answer'), str) or not data['answer'].strip()
            or not isinstance(data.get('citations'), list) or not data['citations']
            or not isinstance(data.get('context'), list) or not data['context']):
        raise ValueError('Live answer must include the selected course, conversation support and sources')


def smoke(base):
    base = base.rstrip('/')
    with urlopen(Request(base, headers={'User-Agent': 'Backbone-GitHub-Actions'}), timeout=30) as response:
        if response.status != 200 or b'Backbone' not in response.read():
            raise RuntimeError('The public homepage did not load')
    wait_ready(base)
    for course, query in [('cs2110', 'Why can the LC-3 global bus only hold one value?'),
                          ('cs2200', 'Why do data hazards happen in a pipeline?')]:
        result = request_json(base + '/api/chat', {'course': course, 'query': query, 'history': []})
        validate_answer(result, course)
        if course == 'cs2200':
            follow = request_json(base + '/api/chat', {'course': course, 'query': 'Can you give a short example?',
                'history': [{'role':'user', 'content':query}, {'role':'assistant', 'content':result['answer'][:4000]}]})
            validate_answer(follow, course)
        print(course + ': live answer and sources verified')


def verify_backend(base, commit, *, request=request_json, sleep=time.sleep, attempts=90):
    wait_for_revision(base, commit, request=request, sleep=sleep, attempts=attempts)
    ready = request(base.rstrip('/') + '/ready')
    if not {'cs2110', 'cs2200'}.issubset(ready.get('courses', [])):
        raise RuntimeError('The tested backend is missing a configured course')


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('backend', 'smoke'):
        raise ValueError('Usage: python scripts/deploy.py backend|smoke')
    if sys.argv[1] == 'backend':
        verify_backend(os.environ['BACKEND_URL'], os.environ['GITHUB_SHA'])
        print('Vercel is serving the tested commit with both courses configured')
    else:
        smoke(os.environ['SITE_URL'])


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # HTTP errors can include URLs; never emit credential-bearing exceptions.
        print('Deployment verification failed (' + type(error).__name__ + '). Check host logs and workflow configuration.', file=sys.stderr)
        sys.exit(1)
