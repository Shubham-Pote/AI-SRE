"""Live faulty-revision recovery check. Requires the disposable demo cluster."""
import json
import time
from pathlib import Path
import requests

API = 'http://api:8000'

def call(method, route, **kwargs):
    response = requests.request(method, API+route, timeout=20, **kwargs)
    response.raise_for_status()
    return response.json()

def main():
    status = call('GET', '/status')
    deadline=time.time()+180
    while (status['stale'] or not status['baseline_ready']) and time.time()<deadline:
        print('Waiting for a verified healthy baseline',flush=True)
        time.sleep(10)
        status=call('GET','/status')
    if status['stale'] or not status['baseline_ready']:
        raise SystemExit('Wait for fresh telemetry and a verified baseline before testing')
    old_mode = status['mode']
    existing = {i['id'] for i in call('GET', '/incidents')}
    started = time.time()
    outcome = None
    failure = None
    cleanup_errors = []
    try:
        call('PUT', '/mode', json={'mode':'automatic'})
        call('POST', '/experiments', json={'fault':'errors'})
        while time.time()-started < 300:
            items = [i for i in call('GET', '/incidents') if i['id'] not in existing and i['payload']['cause']=='faulty_revision']
            if items:
                item = items[0]
                print('Incident',item['id'],item['status'],flush=True)
                if item['status'] in {'resolved','escalated'}:
                    outcome = call('GET', f"/incidents/{item['id']}")
                    break
            time.sleep(10)
    except Exception as exc:
        failure=str(exc)
    finally:
        for method,route,body in [('PUT','/mode',{'mode':old_mode}),('POST','/experiments',{'fault':'none'})]:
            try:
                call(method,route,json=body)
            except Exception as exc:
                cleanup_errors.append(str(exc))
    result = {'started':started,'finished':time.time(),'incident':outcome,'passed':bool(outcome and outcome['status']=='resolved' and not cleanup_errors),'error':failure,'cleanup_errors':cleanup_errors}
    Path(f'data/live-smoke-{int(started)}.json').write_text(json.dumps(result,indent=2))
    Path('data/live-smoke.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    if not result['passed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
