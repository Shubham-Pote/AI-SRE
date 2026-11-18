import os
from datetime import datetime
import requests
import streamlit as st

st.set_page_config(page_title='HealLab | Infrastructure recovery',page_icon=':material/monitor_heart:',layout='wide')
API=os.getenv('CONTROLLER_URL','http://127.0.0.1:8000')
st.title('HealLab')
st.caption('INFRASTRUCTURE OBSERVABILITY / DIAGNOSIS / VERIFIED RECOVERY')
with st.sidebar:
    st.header('Control room')
    st.link_button('Open Grafana',os.getenv('GRAFANA_URL','http://localhost:3000/d/heallab'))
    mode=st.selectbox('Recovery mode',['observe','automatic'])
    if st.button('Apply mode',use_container_width=True):
        try:
            r=requests.put(API+'/mode',json={'mode':mode},timeout=5); r.raise_for_status()
            st.success('Mode updated')
        except requests.RequestException as exc:
            st.error(str(exc))
    if st.button('Stop new recovery actions',type='primary',use_container_width=True):
        try:
            r=requests.put(API+'/mode',json={'mode':'observe'},timeout=5); r.raise_for_status()
            st.success('New actions disabled; verification continues')
        except requests.RequestException as exc:
            st.error(str(exc))
    st.divider()
    st.subheader('Controlled experiments')
    fault=st.selectbox('Demo fault',['none','errors','memory','cpu'])
    if st.button('Apply experiment',use_container_width=True):
        try:
            response=requests.post(API+'/experiments',json={'fault':fault},timeout=15)
            response.raise_for_status()
            st.success('Baseline restored' if fault=='none' else 'Fault injected into demo workload')
        except requests.RequestException as exc:
            st.error(str(exc))
    st.caption('Experiments modify only the isolated demo workload. Select none to restore baseline.')

@st.fragment(run_every=5)
def dashboard():
    try:
        r=requests.get(API+'/status',timeout=5);r.raise_for_status();s=r.json()
        r=requests.get(API+'/incidents',timeout=5);r.raise_for_status();incidents=r.json()
    except requests.RequestException:
        st.error('Controller unavailable. Start the API service and check its address.')
        return
    w=s['telemetry']
    st.subheader('Live workload overview')
    st.caption('Mode: '+s['mode'].upper()+' | Cluster: kind-heal-lab | Namespace: heal-demo')
    if s['stale']:
        st.warning('Telemetry is missing or stale. Automatic recovery requires fresh observations.')
    if s['worker_error']:
        st.error(s['worker_error'])
    cols=st.columns(6)
    for col,label,value in zip(cols,['Requests / sec','Errors','p95 latency','Memory','CPU cores','Ready replicas'],[f"{w.get('rps',0):.1f}",f"{w.get('errors',0):.1%}",f"{w.get('latency',0)*1000:.0f} ms",f"{w.get('memory',0)/1048576:.0f} MiB",f"{w.get('cpu',0):.3f}",str(w.get('ready','-'))]):
        col.metric(label,value)
    try:
        response=requests.get(API+'/telemetry/history',timeout=5)
        response.raise_for_status()
        rows=response.json()
        if rows:
            import pandas as pd
            frame=pd.DataFrame(rows)
            frame['time']=pd.to_datetime(frame['timestamp'],unit='s')
            left,right=st.columns(2)
            with left:
                st.caption('Recent p95 latency (seconds)')
                st.line_chart(frame.set_index('time')[['latency']],height=180,color='#14b8a6')
            with right:
                st.caption('Recent memory (MiB)')
                frame['memory_mib']=frame['memory']/1048576
                st.line_chart(frame.set_index('time')[['memory_mib']],height=180,color='#60a5fa')
    except requests.RequestException:
        st.caption('History temporarily unavailable')
    a,b=st.columns(2)
    with a:
        st.subheader('Intelligence signals')
        st.write('Anomaly detected' if w.get('anomaly') else 'No active ML anomaly')
        st.caption('Model: '+str(w.get('model_version') or 'Not trained - rules remain active'))
        if w.get('model_error'):
            st.warning('Model unavailable; rule-based diagnosis continues.')
        eta=w.get('forecast_seconds')
        st.write(f'Estimated memory limit: {eta:.0f} seconds' if eta is not None else 'Memory forecast: insufficient stable growth evidence')
    with b:
        st.subheader('Recovery outcomes')
        st.write(f"{sum(i['status']=='resolved' for i in incidents)} verified recoveries | {sum(i['status']=='escalated' for i in incidents)} escalations")
        st.caption('API success alone does not count as recovery.')
    st.divider()
    st.subheader('Incident timeline')
    if not incidents:
        st.info('No incidents recorded. Start traffic and run a controlled experiment.')
    for incident in incidents:
        p=incident['payload']
        title=f"#{incident['id']} | {p['cause'].replace('_',' ').title()} | {incident['status'].upper()}"
        with st.expander(title):
            st.write(p['evidence'])
            st.caption(datetime.fromtimestamp(incident['created']).isoformat(timespec='seconds'))
            st.write('Proposed action: '+p['action'])
            try:
                detail=requests.get(API+f"/incidents/{incident['id']}",timeout=5).json()
                for event in detail.get('events',[]):
                    st.write(event['kind'],event['payload'])
            except requests.RequestException:
                st.warning('Could not load event history')
            st.json(p,expanded=False)

dashboard()
