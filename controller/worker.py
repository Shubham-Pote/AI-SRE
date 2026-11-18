import time
from dataclasses import asdict
from controller import store
from controller.core import diagnose, forecast, healthy, allowed, baseline_ready
from controller.adapters import Infrastructure


def main():
    infra = Infrastructure()
    history, active, streak, anomalies = [], None, 0, 0
    # Never replay an action after a crash. Re-observe and verify it instead.
    for item in store.incidents():
        if item['status'] in {'executing','verifying'}:
            active = (item['id'],item['updated'])
            store.event(item['id'],'reconcile',{'message':'Worker restarted; verifying actual state without replay'})
            break
    while True:
        pending_ident = None
        try:
            w = infra.observe()
            history = (history+[w])[-60:]
            prediction = {'anomaly':False,'score':None,'model_version':None}
            try:
                from controller.ml import predict
                prediction = predict(w)
            except FileNotFoundError:
                pass
            except Exception as exc:
                prediction['model_error'] = str(exc)
            anomalies = anomalies+1 if prediction['anomaly'] else 0
            store.set_setting('telemetry',{**asdict(w),'forecast_seconds':forecast(history),**prediction})
            store.set_setting('history',[asdict(item) for item in history])
            store.set_setting('worker_error',None)
            baseline = store.setting('baseline')
            if active:
                ident, started = active
                streak = streak+1 if healthy(w) else 0
                if streak >= 3:
                    store.update(ident,'resolved')
                    store.event(ident,'verified',{'healthy_windows':streak})
                    active, streak = None, 0
                elif time.time()-started > 180:
                    store.update(ident,'escalated')
                    store.event(ident,'verification_failed',{'message':'Recovery deadline exceeded'})
                    active, streak = None, 0
            else:
                if healthy(w):
                    streak += 1
                    if baseline_ready(history,time.time()):
                        store.set_setting('baseline',infra.template())
                else:
                    streak = 0
                revision = baseline['metadata']['annotations'].get('heal/revision') if baseline else None
                diagnosis = diagnose(history,revision)
                if not diagnosis and anomalies >= 3:
                    diagnosis = {'cause':'ml_anomaly','action':'manual','evidence':'Three consecutive anomalous windows; no supported automatic recovery diagnosis'}
                if diagnosis:
                    # De-duplicate ongoing conditions, while allowing recurrence after recovery.
                    condition = diagnosis['cause'] + ':' + store.setting('mode','observe')
                    previous = store.setting('condition')
                    if previous != condition:
                        ident = store.create({**diagnosis,'cluster':infra.context,'namespace':infra.namespace,'workload':infra.workload,'window':asdict(w),'ml':prediction})
                        pending_ident = ident
                        store.set_setting('condition',condition)
                        ok, reason = allowed(w,diagnosis['action'],time.time(),store.setting('last_action',0))
                        store.event(ident,'policy',{'allowed':ok,'reason':reason})
                        if ok and store.setting('mode','observe') == 'automatic':
                            fresh = infra.observe()
                            ok, reason = allowed(fresh,diagnosis['action'],time.time(),store.setting('last_action',0))
                            if ok and store.setting('mode','observe') == 'automatic':
                                store.update(ident,'executing')
                                store.set_setting('last_action',time.time())
                                try:
                                    result = infra.execute(diagnosis['action'],baseline)
                                    store.event(ident,'action',result)
                                    store.update(ident,'verifying')
                                    active, streak = (ident,time.time()), 0
                                except Exception as exc:
                                    store.event(ident,'action_error',{'error':str(exc)})
                                    store.update(ident,'escalated')
                            else:
                                store.update(ident,'escalated')
                        else:
                            store.update(ident,'observed' if ok else 'escalated')
                elif healthy(w):
                    store.set_setting('condition',None)
        except Exception as exc:
            streak, anomalies = 0, 0
            store.set_setting('worker_error',str(exc))
            if pending_ident and not active:
                store.update(pending_ident,'escalated')
                store.event(pending_ident,'observation_error',{'error':str(exc)})
            if active and time.time()-active[1] > 180:
                store.update(active[0],'escalated')
                store.event(active[0],'verification_failed',{'error':str(exc)})
                active = None
        time.sleep(15)

if __name__ == '__main__':
    main()
