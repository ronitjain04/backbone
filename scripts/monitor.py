"""Read-only live provider monitor. It has no deployment commands or credentials."""
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
import os
import time
from urllib.error import HTTPError
from scripts import deploy

class MonitorError(RuntimeError):
    pass


def retry_delay(value):
    try:return max(0,int(value))
    except (TypeError,ValueError):
        try:return max(0,int((parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()))
        except (TypeError,ValueError,OverflowError):return None


def request_with_retry(url,data=None,*,request=deploy.request_json,sleep=time.sleep,attempts=2,max_wait=60):
    for attempt in range(attempts):
        try:return request(url,data)
        except HTTPError as error:
            if error.code not in (429,502,503,504):raise MonitorError('Live service returned an unexpected HTTP status') from None
            delay=retry_delay(error.headers.get('Retry-After'))
            if delay is not None and delay>max_wait:
                raise MonitorError('Live service quota/rate limit exceeds the monitor wait budget; no early retry was made') from None
            if attempt+1==attempts:raise MonitorError('Live service unavailable or rate-limited after bounded retries (HTTP '+str(error.code)+'); inspect provider/runtime status') from None
            sleep(delay if delay is not None else min(5*(attempt+1),max_wait))
        except OSError:
            if attempt+1==attempts:raise MonitorError('Live network/service unavailable after bounded retries') from None
            sleep(min(5*(attempt+1),max_wait))


def main():
    def opener(request,timeout):
        return request_with_retry(request,request=lambda req,data:deploy.urlopen(req,timeout=timeout))
    try:
        deploy.smoke(os.environ['SITE_URL'],request=request_with_retry,opener=opener)
    except MonitorError as error:
        print('Live availability monitor: '+str(error));raise SystemExit(1) from None
    except Exception as error:
        print('Live response/configuration verification failed ('+type(error).__name__+'). No deployment was attempted.')
        raise SystemExit(1) from None

if __name__=='__main__':main()
