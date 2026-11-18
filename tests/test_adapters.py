from types import SimpleNamespace as S
from unittest.mock import Mock, patch
import pytest
from controller.adapters import Infrastructure

def infra():
    instance=Infrastructure.__new__(Infrastructure)
    instance.namespace='heal-demo';instance.workload='demo';instance.prometheus='http://prometheus'
    instance.apps=Mock();instance.core=Mock()
    instance.apps.read_namespaced_deployment.return_value=S(spec=S(replicas=2))
    return instance

def pod(name,uid):
    return S(metadata=S(name=name,uid=uid,deletion_timestamp=None),status=S(conditions=[S(type='Ready',status='True')]))

def test_replaces_highest_memory_pod_with_uid_precondition():
    i=infra();i.core.list_namespaced_pod.return_value=S(items=[pod('low','a'),pod('high','b')])
    reply=Mock();reply.json.return_value={'data':{'result':[{'metric':{'pod':'low'},'value':[0,'10']},{'metric':{'pod':'high'},'value':[0,'99']}]}}
    with patch('requests.get',return_value=reply):
        assert i.execute('replace_pod',None)=={'pod':'high'}
    call=i.core.delete_namespaced_pod.call_args
    assert call.args==('high','heal-demo')
    assert call.kwargs['body'].preconditions.uid=='b'

def test_no_rollback_without_verified_template():
    with pytest.raises(ValueError,match='healthy template'):
        infra().execute('rollback',None)

def test_api_error_propagates_for_escalation():
    i=infra();i.apps.patch_namespaced_deployment_scale.side_effect=RuntimeError('Unavailable')
    with pytest.raises(RuntimeError): i.execute('scale',None)
