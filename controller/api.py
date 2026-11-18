import os
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from controller import store

app = FastAPI(title='HealLab control plane')

class Mode(BaseModel):
    mode: str

@app.get('/health')
def health():
    return {'status':'ok','worker_error':store.setting('worker_error')}

@app.get('/status')
def status():
    telemetry = store.setting('telemetry',{})
    return {'mode':store.setting('mode','observe'),'telemetry':telemetry,'stale':time.time()-telemetry.get('timestamp',0)>45,'worker_error':store.setting('worker_error'), 'baseline_ready':bool(store.setting('baseline'))}

@app.put('/mode')
def mode(body:Mode):
    if body.mode not in {'observe','automatic'}:
        raise HTTPException(422,'Choose observe or automatic')
    store.set_setting('mode',body.mode)
    return {'mode':body.mode}

@app.get('/incidents')
def incidents():
    return store.incidents()

@app.get('/telemetry/history')
def history():
    return store.setting('history',[])

@app.get('/incidents/{ident}')
def detail(ident:int):
    found = next((i for i in store.incidents() if i['id']==ident),None)
    if not found:
        raise HTTPException(404,'Incident not found')
    return {**found,'events':store.events(ident)}

class Experiment(BaseModel):
    fault: str

@app.post('/experiments')
def experiment(body:Experiment):
    if body.fault not in {'none','memory','cpu','errors'}:
        raise HTTPException(422,'Unsupported fault')
    from controller.adapters import Infrastructure
    revision='good' if body.fault=='none' else 'experiment-'+str(int(time.time()))
    try:
        infra=Infrastructure()
        infra.apps.patch_namespaced_deployment('demo',infra.namespace,{'spec':{'template':{'metadata':{'annotations':{'heal/revision':revision}},'spec':{'containers':[{'name':'demo','env':[{'name':'FAULT','value':body.fault}]}]}}}})
        if body.fault=='none':
            infra.apps.patch_namespaced_deployment_scale('demo',infra.namespace,{'spec':{'replicas':2}})
            store.set_setting('condition',None)
        record={'timestamp':time.time(),'fault':body.fault,'revision':revision}
        store.set_setting('experiment',record)
        return record
    except Exception as exc:
        raise HTTPException(503,str(exc)) from exc

@app.get('/experiments')
def current_experiment():
    return store.setting('experiment',{})
