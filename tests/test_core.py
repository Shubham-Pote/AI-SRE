from controller.core import Window, allowed, diagnose, forecast, healthy

def test_stale_telemetry_blocks_action():
    assert not allowed(Window(0),'scale',1000)[0]

def test_replica_limit_and_cooldown():
    assert not allowed(Window(1000,replicas=3),'scale',1000)[0]
    assert not allowed(Window(1000),'scale',1000,900)[0]

def test_preserve_available_replica():
    assert not allowed(Window(1000,ready=1),'replace_pod',1000)[0]

def test_bad_revision_requires_baseline():
    h=[Window(i,errors=.5,revision='bad') for i in range(3)]
    assert diagnose(h,'good')['action']=='rollback'
    assert diagnose(h,None)['action']=='manual'

def test_transient_spike_does_not_trigger():
    assert diagnose([Window(0),Window(15),Window(30,errors=.8)],'good') is None

def test_forecast_and_memory_diagnosis():
    h=[Window(i*15,memory=160000000+i*5000000) for i in range(8)]
    assert 0 < forecast(h) < 300
    assert diagnose(h,'good')['action']=='replace_pod'

def test_constant_memory_has_no_forecast():
    assert forecast([Window(i*15,memory=100) for i in range(8)]) is None

def test_health_requires_real_traffic():
    assert not healthy(Window(0))
    assert healthy(Window(0,rps=10,latency=.02))

def test_observation_gaps_reset_diagnostic_evidence():
    h=[Window(0,errors=.5),Window(15,errors=.5),Window(100,errors=.5)]
    assert diagnose(h,'good') is None

def test_nonfinite_and_future_telemetry_block_actions():
    assert not allowed(Window(1000,cpu=float('nan')),'scale',1000)[0]
    assert not allowed(Window(1100),'scale',1000)[0]

def test_new_revision_cannot_inherit_previous_healthy_history():
    from controller.core import baseline_ready
    old=[Window(t,rps=5,revision='good') for t in range(0,150,15)]
    new=[Window(150,rps=5,revision='bad')]
    assert not baseline_ready(old+new,150)
    assert baseline_ready(old,150)

def test_incomplete_rollout_is_never_a_healthy_baseline():
    from controller.core import baseline_ready
    h=[Window(t,rps=5,revision='new',rollout_complete=False) for t in range(0,150,15)]
    assert not baseline_ready(h,150)
    assert not healthy(h[-1])
