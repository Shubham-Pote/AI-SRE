from fastapi.testclient import TestClient
from controller import store
from controller.api import app
import pytest

@pytest.fixture
def api(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DB',str(tmp_path/'test.db'))
    return TestClient(app)

def test_missing_telemetry_and_observe_default(api):
    result=api.get('/status').json()
    assert result['mode']=='observe'
    assert result['stale']

def test_mode_validation_and_stop(api):
    assert api.put('/mode',json={'mode':'arbitrary'}).status_code==422
    assert api.put('/mode',json={'mode':'automatic'}).status_code==200
    assert api.get('/status').json()['mode']=='automatic'
    api.put('/mode',json={'mode':'observe'})
    assert api.get('/status').json()['mode']=='observe'

def test_incident_persistence_and_history(api):
    ident=store.create({'cause':'unknown','action':'manual'})
    store.event(ident,'policy',{'allowed':False})
    store.update(ident,'escalated')
    data=api.get(f'/incidents/{ident}').json()
    assert data['status']=='escalated'
    assert data['events'][0]['payload']['allowed'] is False
    assert api.get('/incidents/999').status_code==404

def test_arbitrary_fault_is_rejected(api):
    assert api.post('/experiments',json={'fault':'delete-cluster'}).status_code==422
