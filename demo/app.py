import asyncio
import os
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

REQUESTS = Counter('demo_requests_total','Completed work requests',['status'])
LATENCY = Histogram('demo_latency_seconds','Work request latency',buckets=(.01,.05,.1,.2,.4,.8,1,2,5))
for label in ['ok','error']:
    REQUESTS.labels(label).inc(0)
allocation=[]

@asynccontextmanager
async def lifespan(app):
    async def leak():
        while True:
            if os.getenv('DEMO_FAULTS')=='true' and os.getenv('FAULT')=='memory':
                allocation.append(bytearray(2*1024*1024))
            await asyncio.sleep(5)
    task=asyncio.create_task(leak())
    yield
    task.cancel()

app=FastAPI(lifespan=lifespan)

@app.get('/health')
def health():
    return {'ok':True}

@app.get('/ready')
def ready():
    return {'ready':True}

@app.get('/work')
async def work(response:Response):
    start=time.perf_counter()
    fault=os.getenv('FAULT','none') if os.getenv('DEMO_FAULTS')=='true' else 'none'
    if fault=='cpu':
        await asyncio.to_thread(lambda: sum(i*i for i in range(1500000)))
    else:
        await asyncio.sleep(.02)
    failed=fault=='errors'
    response.status_code=500 if failed else 200
    REQUESTS.labels('error' if failed else 'ok').inc()
    LATENCY.observe(time.perf_counter()-start)
    return {'ok':not failed,'pod':os.getenv('HOSTNAME','local')}

@app.get('/metrics')
def metrics():
    return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
