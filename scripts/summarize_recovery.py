"""Aggregate preserved live recovery trials without counting duplicate latest files."""
import json
import statistics
from pathlib import Path

trials=[]
for path in sorted(Path('data').glob('live-smoke-*.json')):
    trial=json.loads(path.read_text())
    incident=trial.get('incident')
    trials.append({
        'file':path.name,
        'passed':trial['passed'],
        'detection_seconds':incident['created']-trial['started'] if incident else None,
        'verified_recovery_seconds':incident['updated']-trial['started'] if incident and trial['passed'] else None,
        'model_version':incident['payload'].get('ml',{}).get('model_version') if incident else None,
    })
successes=[t for t in trials if t['passed']]
summary={
    'trials':trials,
    'successful_trials':len(successes),
    'total_trials':len(trials),
    'median_verified_recovery_seconds':statistics.median(t['verified_recovery_seconds'] for t in successes) if successes else None,
    'limitation':'Functional smoke trials, not a randomized comparative reliability benchmark.',
}
Path('data/recovery-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
