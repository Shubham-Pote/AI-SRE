"""Explicit, bounded fault injection into the dedicated demo workload."""
import argparse
import json
import time
from pathlib import Path
from controller.adapters import Infrastructure
from controller import store

parser=argparse.ArgumentParser()
parser.add_argument('fault',choices=['none','memory','cpu','errors'])
args=parser.parse_args()
infra=Infrastructure()
revision='good' if args.fault=='none' else 'experiment-'+str(int(time.time()))
patch={'spec':{'template':{'metadata':{'annotations':{'heal/revision':revision}},'spec':{'containers':[{'name':'demo','env':[{'name':'FAULT','value':args.fault}]}]}}}}
infra.apps.patch_namespaced_deployment('demo',infra.namespace,patch)
if args.fault=='none':
    infra.apps.patch_namespaced_deployment_scale('demo',infra.namespace,{'spec':{'replicas':2}})
    store.set_setting('condition',None)
record={'timestamp':time.time(),'fault':args.fault,'revision':revision}
with Path('data/experiments.jsonl').open('a') as f:
    f.write(json.dumps(record)+'\n')
print(json.dumps(record))
