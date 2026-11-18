"""Train on complete healthy runs; validation must be a separate run."""
import argparse
import json
import time
from pathlib import Path
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from controller.core import Window

p=argparse.ArgumentParser()
p.add_argument('--train',nargs='+',required=True)
p.add_argument('--validation',required=True)
a=p.parse_args()
if Path(a.validation).resolve() in [Path(v).resolve() for v in a.train]:
    p.error('Validation must be a separate experiment run')
def read(path):
    return [Window(**json.loads(line)).features() for line in Path(path).read_text().splitlines() if line]
x=[row for path in a.train for row in read(path)]
v=read(a.validation)
if len(x)<40 or len(v)<10: p.error('Collect at least 40 training and 10 validation windows')
model=IsolationForest(n_estimators=100,random_state=42,contamination='auto').fit(x)
model.offset_=float(np.quantile(model.score_samples(v),.01))
Path('data').mkdir(exist_ok=True)
joblib.dump({'model':model,'version':str(int(time.time())),'training_runs':a.train,'validation_run':a.validation},'data/model.joblib')
print('Saved model; validate with independent fault runs before making accuracy claims')
