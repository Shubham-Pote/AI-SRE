"""Pure, testable diagnostic and recovery policy."""
from dataclasses import dataclass, asdict
import math

@dataclass
class Window:
    timestamp: float
    rps: float = 0
    errors: float = 0
    latency: float = 0
    memory: float = 0
    memory_limit: float = 268435456
    cpu: float = 0
    ready: int = 2
    replicas: int = 2
    revision: str = ""
    valid: bool = True
    rollout_complete: bool = True

    def features(self):
        return [self.rps, self.errors, self.latency, self.memory / self.memory_limit, self.cpu, self.ready]


def forecast(history):
    points = [w for w in history[-12:] if w.valid]
    if len(points) < 6:
        return None
    if any(b.timestamp-a.timestamp > 45 for a,b in zip(points,points[1:])):
        return None
    xs = [w.timestamp - points[0].timestamp for w in points]
    ys = [w.memory for w in points]
    mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
    variance = sum((x-mx)**2 for x in xs)
    if not variance:
        return None
    slope = sum((x-mx)*(y-my) for x,y in zip(xs,ys))/variance
    total = sum((y-my)**2 for y in ys)
    residual = sum((y-(my+slope*(x-mx)))**2 for x,y in zip(xs,ys))
    if slope <= 0 or not total or 1-residual/total < .8:
        return None
    return max(0, (points[-1].memory_limit-points[-1].memory)/slope)


def diagnose(history, healthy_revision):
    if len(history) < 3 or not all(w.valid for w in history[-3:]) or any(b.timestamp-a.timestamp > 45 for a,b in zip(history[-3:],history[-2:])):
        return None
    recent = history[-3:]
    last = recent[-1]
    if all(w.errors > .10 for w in recent):
        if healthy_revision and last.revision != healthy_revision:
            return {"cause": "faulty_revision", "action": "rollback", "evidence": "Errors exceed 10% after revision change"}
        return {"cause": "unknown_errors", "action": "manual", "evidence": "Sustained errors without a known healthy revision change"}
    eta = forecast(history)
    if eta is not None and eta < 300 and last.memory/last.memory_limit > .55:
        return {"cause": "memory_growth", "action": "replace_pod", "evidence": f"Stable memory growth; limit estimated in {eta:.0f}s"}
    if all(w.cpu > .15 and w.latency > .4 for w in recent):
        return {"cause": "overload", "action": "scale", "evidence": "Sustained CPU pressure and request latency"}
    if all(w.latency > 1 or w.ready < 1 for w in recent):
        return {"cause": "unknown_degradation", "action": "manual", "evidence": "Unhealthy workload without a supported diagnosis"}
    return None


def healthy(w):
    return w.valid and w.rollout_complete and w.rps > 0 and w.ready >= 2 and w.errors < .02 and w.latency < .4 and w.memory/w.memory_limit < .8

def baseline_ready(history, now):
    if len(history)<3 or not all(healthy(w) for w in history[-3:]):
        return False
    revision=history[-1].revision
    same=[]
    for w in reversed(history):
        if w.revision!=revision or not w.rollout_complete:
            break
        same.append(w)
    return len(same)>=3 and now-same[-1].timestamp>=90


def allowed(w, action, now, last_action=0):
    if not w.valid or not 0 <= now-w.timestamp <= 45 or any(not math.isfinite(v) for v in w.features()):
        return False, "Telemetry is stale or incomplete"
    if now-last_action < 300:
        return False, "Five-minute cooldown"
    if action == "scale" and w.replicas >= 3:
        return False, "Replica ceiling reached"
    if action == "replace_pod" and w.ready < 2:
        return False, "A second ready replica is required"
    if action not in {"scale", "replace_pod", "rollback"}:
        return False, "No supported automatic action"
    return True, "Policy checks passed"
