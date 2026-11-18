import argparse
import json
import time
from dataclasses import asdict
from controller.adapters import Infrastructure
p=argparse.ArgumentParser()
p.add_argument('--output',required=True)
p.add_argument('--windows',type=int,default=60)
a=p.parse_args()
i=Infrastructure()
with open(a.output,'w') as f:
    for _ in range(a.windows):
        f.write(json.dumps(asdict(i.observe()))+'\n'); f.flush(); time.sleep(15)
