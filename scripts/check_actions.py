"""Integration check of allowlisted Kubernetes tools, not a controller-policy benchmark."""
import json
import time
from pathlib import Path
from controller.adapters import Infrastructure

def wait_for(condition, timeout=120):
    deadline=time.time()+timeout
    while time.time()<deadline:
        if condition():
            return
        time.sleep(5)
    raise RuntimeError('Kubernetes action did not converge before timeout')

def main():
    infra=Infrastructure()
    before=infra.deployment().spec.replicas
    if before!=2:
        raise SystemExit('Restore the demo baseline with two replicas first')
    report={}
    try:
        report['scale']=infra.execute('scale',None)
        wait_for(lambda: infra.deployment().status.ready_replicas==3)
        # Wait for a new pod to appear in the metrics used to choose the target.
        time.sleep(20)
        report['replace_pod']=infra.execute('replace_pod',None)
        name=report['replace_pod']['pod']
        def replaced():
            pods=infra.core.list_namespaced_pod(infra.namespace,label_selector='app=demo').items
            return name not in [p.metadata.name for p in pods] and infra.deployment().status.ready_replicas==3
        wait_for(replaced)
        report['passed']=True
    finally:
        infra.apps.patch_namespaced_deployment_scale('demo',infra.namespace,{'spec':{'replicas':before}})
        Path('data/action-check.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    main()
