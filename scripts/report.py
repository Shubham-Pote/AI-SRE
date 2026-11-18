import argparse
import json
import statistics
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('runs',nargs='+')
a=p.parse_args()
for name in a.runs:
    rows=[json.loads(line) for line in Path(name).read_text().splitlines() if line]
    if not rows: continue
    latency=sorted(r['latency'] for r in rows)
    print(json.dumps({'run':name,'requests':len(rows),'failed':sum(r['status']!=200 for r in rows),'median_latency':statistics.median(latency),'p95_latency':latency[min(len(latency)-1,int(len(latency)*.95))]}))
