import os
import time
import requests
from kubernetes import client, config
from controller.core import Window

class Infrastructure:
    def __init__(self):
        self.context = os.getenv("KUBE_CONTEXT", "kind-heal-lab")
        self.namespace = os.getenv("NAMESPACE", "heal-demo")
        self.workload = "demo"
        config.load_kube_config(context=self.context)
        self.apps, self.core = client.AppsV1Api(), client.CoreV1Api()
        self.prometheus = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

    def deployment(self):
        return self.apps.read_namespaced_deployment(self.workload, self.namespace)

    def query(self, expression):
        response = requests.get(self.prometheus+'/api/v1/query', params={'query':expression}, timeout=8)
        response.raise_for_status()
        data = response.json()['data']['result']
        if not data:
            raise ValueError('Missing metric: '+expression)
        value = float(data[0]['value'][1])
        import math
        if not math.isfinite(value):
            raise ValueError('Non-finite metric: '+expression)
        return value

    def observe(self):
        d = self.deployment()
        # A successful scrape is required: Prometheus can otherwise return old samples.
        if self.query('min(up{job="demo"})') != 1:
            raise ValueError('One or more application targets are unavailable')
        if self.query('max(time() - timestamp(up{job="demo"}))') > 45:
            raise ValueError('Application scrape data is stale')
        count = self.query('sum(rate(demo_requests_total[1m]))')
        errors = self.query('sum(rate(demo_requests_total{status="error"}[1m]))')
        latency = self.query('histogram_quantile(0.95,sum(rate(demo_latency_seconds_bucket[1m])) by (le))') if count > 0 else 0
        return Window(time.time(), count, errors/max(count,.001),
            latency,
            self.query('max(process_resident_memory_bytes{job="demo"})'),
            268435456, self.query('max(rate(process_cpu_seconds_total{job="demo"}[1m]))'),
            d.status.ready_replicas or 0, d.spec.replicas,
            d.spec.template.metadata.annotations.get('heal/revision','good'),
            rollout_complete=(d.status.observed_generation == d.metadata.generation and d.status.updated_replicas == d.spec.replicas and d.status.replicas == d.spec.replicas and d.status.available_replicas == d.spec.replicas))

    def template(self):
        return client.ApiClient().sanitize_for_serialization(self.deployment().spec.template)

    def execute(self, action, baseline):
        d = self.deployment()
        if action == 'scale':
            target = min(3,d.spec.replicas+1)
            self.apps.patch_namespaced_deployment_scale(self.workload,self.namespace,{'spec':{'replicas':target}})
            return {'replicas':target}
        if action == 'rollback':
            if not baseline:
                raise ValueError('No verified healthy template')
            self.apps.patch_namespaced_deployment(self.workload,self.namespace,{'spec':{'template':baseline}})
            return {'revision':baseline['metadata']['annotations']['heal/revision']}
        if action == 'replace_pod':
            pods = self.core.list_namespaced_pod(self.namespace,label_selector='app=demo').items
            ready = [p for p in pods if not p.metadata.deletion_timestamp and any(c.type=='Ready' and c.status=='True' for c in (p.status.conditions or []))]
            if len(ready)<2:
                raise ValueError('Not enough ready pods')
            # Select the actual highest-memory pod, not an arbitrary replica.
            response = requests.get(self.prometheus+'/api/v1/query',params={'query':'process_resident_memory_bytes{job="demo"}'},timeout=8)
            response.raise_for_status()
            usage = {r['metric'].get('pod'):float(r['value'][1]) for r in response.json()['data']['result']}
            candidates = [p for p in ready if p.metadata.name in usage]
            if not candidates:
                raise ValueError('No pod-level memory evidence')
            target = max(candidates,key=lambda p:usage[p.metadata.name])
            self.core.delete_namespaced_pod(target.metadata.name,self.namespace,body=client.V1DeleteOptions(preconditions=client.V1Preconditions(uid=target.metadata.uid)))
            return {'pod':target.metadata.name}
        raise ValueError('Unsupported action')
