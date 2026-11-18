from pathlib import Path
import joblib

MODEL = Path('data/model.joblib')

def predict(window):
    bundle = joblib.load(MODEL)
    features = [window.features()]
    score = float(bundle['model'].decision_function(features)[0])
    return {'anomaly':score<0,'score':score,'model_version':bundle['version']}
