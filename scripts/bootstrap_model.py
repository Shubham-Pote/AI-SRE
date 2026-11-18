"""Create an exploratory model from real healthy telemetry, with a time-separated holdout.

This is a demo baseline, not a substitute for independent experimental validation.
"""
import json
import math
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
import requests
from controller.core import Window, healthy

QUERIES = {
    'rps':'sum(rate(demo_requests_total[1m]))',
    'errors':'sum(rate(demo_requests_total{status="error"}[1m])) / clamp_min(sum(rate(demo_requests_total[1m])),0.001)',
    'latency':'histogram_quantile(0.95,sum(rate(demo_latency_seconds_bucket[1m])) by (le))',
    'memory':'max(process_resident_memory_bytes{job="demo"})',
    'cpu':'max(rate(process_cpu_seconds_total{job="demo"}[1m]))',
    'ready':'kube_deployment_status_replicas_available{deployment="demo"}',
    'replicas':'kube_deployment_spec_replicas{deployment="demo"}',
    'up':'min(up{job="demo"})',
}

def main():
    end = int(time.time()//15)*15
    url = os.getenv('PROMETHEUS_URL','http://heal-lab-control-plane:30090')
    fields = {}
    for name, query in QUERIES.items():
        response = requests.get(url+'/api/v1/query_range',params={'query':query,'start':end-3600,'end':end,'step':15},timeout=20)
        response.raise_for_status()
        data=response.json()['data']['result']
        if len(data)!=1:
            raise SystemExit(f'Expected one aggregate series for {name}; got {len(data)}')
        fields[name]={int(t):float(v) for t,v in data[0]['values'] if math.isfinite(float(v))}
    timestamps=sorted(set.intersection(*(set(v) for v in fields.values())))
    exclusions=[]
    for smoke in Path('data').glob('live-smoke*.json'):
        trial=json.loads(smoke.read_text())
        interval=(trial['started'],trial['finished']+60)
        if interval not in exclusions:
            exclusions.append(interval)
    windows=[]
    fault_windows=[]
    for timestamp in timestamps:
        values={name:series[timestamp] for name,series in fields.items()}
        up=values.pop('up')
        w=Window(timestamp=timestamp,**values)
        if any(start <= timestamp <= stop for start,stop in exclusions):
            if up==1 and w.errors>.1:
                fault_windows.append(w)
            continue
        if up==1 and healthy(w) and w.cpu<.1 and w.memory/w.memory_limit<.55:
            windows.append(w)
    # The final ten healthy points are a holdout. Leave at least a one-minute gap
    # so their rate windows cannot overlap training feature windows.
    if len(windows)<55:
        raise SystemExit(f'Only {len(windows)} healthy windows available; need at least 55. Run healthy traffic longer.')
    validation=windows[-10:]
    training=[w for w in windows[:-10] if w.timestamp < validation[0].timestamp-60]
    if len(training)<40:
        raise SystemExit('Need 40 training windows after the holdout gap')
    for name,rows in [('bootstrap-train',training),('bootstrap-validation',validation)]:
        Path(f'data/{name}.jsonl').write_text(''.join(json.dumps(asdict(w))+'\n' for w in rows))
    subprocess.run([sys.executable,'scripts/train.py','--train','data/bootstrap-train.jsonl','--validation','data/bootstrap-validation.jsonl'],check=True)
    summary={'source':'real Prometheus observations','training_windows':len(training),'validation_windows':len(validation),'gap_seconds':validation[0].timestamp-training[-1].timestamp,'excluded_fault_intervals':exclusions,'limitation':'Exploratory healthy baseline; separate fault and normal-load evaluation required.'}
    Path('data/model-provenance.json').write_text(json.dumps(summary,indent=2))
    if fault_windows:
        import joblib
        bundle=joblib.load('data/model.joblib')
        predictions=bundle['model'].predict([w.features() for w in fault_windows])
        evaluation={'fault_windows':len(fault_windows),'flagged_fault_windows':int(sum(predictions==-1)), 'model_version':bundle['version'],'note':'Descriptive replay of one excluded fault experiment; not a general accuracy estimate. Rules independently handle faulty revisions.'}
        Path('data/model-evaluation.json').write_text(json.dumps(evaluation,indent=2))
        print(json.dumps(evaluation,indent=2))
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    main()
