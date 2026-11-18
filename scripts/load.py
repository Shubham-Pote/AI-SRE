import argparse
import asyncio
import json
import random
import time
import httpx

async def run(args):
    rng=random.Random(args.seed)
    end=time.monotonic()+args.seconds
    results=[]
    semaphore=asyncio.Semaphore(30)
    async with httpx.AsyncClient(timeout=10,limits=httpx.Limits(max_keepalive_connections=0)) as client:
        async def request():
            async with semaphore:
                start=time.monotonic()
                try:
                    response=await client.get(args.url+'/work')
                    code=response.status_code
                except httpx.HTTPError:
                    code=0
                results.append({'time':time.time(),'latency':time.monotonic()-start,'status':code})
        tasks=set()
        while time.monotonic()<end:
            task=asyncio.create_task(request());tasks.add(task);task.add_done_callback(tasks.discard)
            await asyncio.sleep(rng.uniform(.8,1.2)/args.rps)
        await asyncio.gather(*tasks)
    with open(args.output,'w') as f:
        for row in results: f.write(json.dumps(row)+'\n')
    print(f'{len(results)} requests; {sum(r["status"]!=200 for r in results)} failures')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--url',default='http://demo.heal-demo.svc.cluster.local:8080')
    p.add_argument('--rps',type=float,default=5)
    p.add_argument('--seconds',type=int,default=300)
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--output',default='data/load.jsonl')
    args=p.parse_args()
    if args.rps<=0: p.error('rps must be positive')
    asyncio.run(run(args))
