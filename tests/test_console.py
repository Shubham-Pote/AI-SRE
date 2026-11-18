from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

class Reply:
    def __init__(self,data): self.data=data
    def raise_for_status(self): pass
    def json(self): return self.data

def test_console_renders_live_status_without_exceptions():
    def get(url,**kwargs):
        if url.endswith('/status'):
            return Reply({'mode':'observe','stale':False,'worker_error':None,'telemetry':{'rps':5,'errors':0,'latency':.03,'memory':64000000,'ready':2}})
        return Reply([])
    with patch('requests.get',side_effect=get):
        app=AppTest.from_file('console/app.py').run(timeout=15)
    assert not app.exception
    assert app.title[0].value=='HealLab'
    assert len(app.metric)==6

def test_console_handles_offline_controller():
    import requests
    with patch('requests.get',side_effect=requests.ConnectionError()):
        app=AppTest.from_file('console/app.py').run(timeout=15)
    assert not app.exception
    assert 'Controller unavailable' in app.error[0].value
