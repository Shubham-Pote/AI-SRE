from unittest.mock import Mock
import pytest
from controller import store, worker
from controller.core import Window


class EndRun(BaseException):
    pass


def run_worker(monkeypatch, tmp_path, windows, ticks, resume=False):
    from controller import ml
    monkeypatch.setattr(ml, 'predict', lambda _: {'anomaly':False,'score':None,'model_version':None})
    monkeypatch.setattr(store, 'DB', str(tmp_path / 'worker.db'))
    monkeypatch.setattr(worker.time, 'time', lambda: 1000)
    baseline = {'metadata': {'annotations': {'heal/revision': 'good'}}}
    store.set_setting('baseline', baseline)
    store.set_setting('mode', 'automatic')
    if resume:
        ident = store.create({'cause': 'faulty_revision', 'action': 'rollback'})
        store.update(ident, 'executing')
    infra = Mock(context='test', namespace='heal-demo', workload='demo')
    infra.observe.side_effect = windows
    infra.template.return_value = baseline
    infra.execute.return_value = {'revision': 'good'}
    monkeypatch.setattr(worker, 'Infrastructure', lambda: infra)
    counter = 0

    def sleep(_):
        nonlocal counter
        counter += 1
        if counter >= ticks:
            raise EndRun()

    monkeypatch.setattr(worker.time, 'sleep', sleep)
    with pytest.raises(EndRun):
        worker.main()
    return infra


def test_recovery_requires_three_healthy_windows(monkeypatch, tmp_path):
    bad = Window(1000, rps=5, errors=.8, revision='bad')
    good = Window(1000, rps=5, latency=.02, revision='good')
    infra = run_worker(monkeypatch, tmp_path, [bad]*4+[good]*3, 6)
    infra.execute.assert_called_once()
    item = store.incidents()[0]
    assert item['status'] == 'resolved'
    assert [e['kind'] for e in store.events(item['id'])] == ['policy', 'action', 'verified']


def test_restart_reconciles_without_replaying_action(monkeypatch, tmp_path):
    good = Window(1000, rps=5, latency=.02, revision='good')
    infra = run_worker(monkeypatch, tmp_path, [good]*3, 3, resume=True)
    infra.execute.assert_not_called()
    assert store.incidents()[0]['status'] == 'resolved'


def test_action_failure_escalates(monkeypatch, tmp_path):
    bad = Window(1000, rps=5, errors=.8, revision='bad')
    # An unavailable fresh observation must not execute an action.
    infra = run_worker(monkeypatch, tmp_path, [bad]*3+[RuntimeError('offline')], 3)
    infra.execute.assert_not_called()
    assert store.setting('worker_error') == 'offline'
    assert store.incidents()[0]['status'] == 'escalated'
