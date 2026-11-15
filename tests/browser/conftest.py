import socket
import threading
import time
import pytest
import uvicorn
from tests.browser.support.server import create_fixture_app,TEACHER_TOKEN

pytest_plugins=['website.backend.tests.conftest']

# Each test owns a dynamic local origin; do not use the plugin's session URL probe.
@pytest.fixture(scope='session')
def base_url():
    return None

@pytest.fixture
def live_server(practice_database_url,monkeypatch):
    monkeypatch.setenv('PRACTICE_OWNER_TOKEN',TEACHER_TOKEN)
    monkeypatch.delenv('PRACTICE_AUTO_MIGRATE',raising=False)
    app=create_fixture_app(practice_database_url)
    sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,log_level='warning',lifespan='on'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        deadline=time.monotonic()+10
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Synthetic browser server did not start')
            time.sleep(.02)
        yield f'http://127.0.0.1:{port}'
    finally:
        server.should_exit=True;thread.join(timeout=10);sock.close()
        if thread.is_alive():raise RuntimeError('Synthetic browser server did not stop')
