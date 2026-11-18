import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from controller import ml
from controller.core import Window

def test_inference_returns_version_and_native_json_values(tmp_path, monkeypatch):
    path=tmp_path/'model.joblib'
    monkeypatch.setattr(ml,'MODEL',path)
    rng=np.random.default_rng(42)
    model=IsolationForest(random_state=42).fit(rng.normal(size=(60,6)))
    joblib.dump({'model':model,'version':'test-run'},path)
    result=ml.predict(Window(0,rps=5))
    assert isinstance(result['score'],float)
    assert isinstance(result['anomaly'],bool)
    assert result['model_version']=='test-run'

def test_missing_model_is_explicit(tmp_path,monkeypatch):
    import pytest
    monkeypatch.setattr(ml,'MODEL',tmp_path/'missing.joblib')
    with pytest.raises(FileNotFoundError): ml.predict(Window(0))
