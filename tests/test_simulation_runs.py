import pytest
from threading import Event

from backend.main import app


def finish(client, run_id):
    app.state.runs.wait(run_id, timeout=3)
    return client.get('/api/runs/' + run_id).json()


@pytest.mark.parametrize('scenario,expected_status,attempts', [
    ('success', 'ok', 1), ('rider_rejected', 'rejected', 2),
    ('retry_success', 'ok', 2), ('provider_error', 'error', 1),
])
def test_simulation_pipeline_runs_without_network(client, monkeypatch, scenario, expected_status, attempts):
    monkeypatch.setenv('OPENAI_API_KEY', 'must-never-leave-process')
    monkeypatch.setattr('backend.core.llm.requests.post', lambda *a, **k: pytest.fail('Network forbidden'))
    response = client.post('/api/runs', json={'case_id': 'RYDE-2026-0001', 'scenario': scenario})
    assert response.status_code == 202
    run_id = response.json()['run_id']
    snapshot = finish(client, run_id)
    assert snapshot['status'] == 'completed'
    result = snapshot['result']
    assert result['run_id'] == run_id
    assert result['ruling']['amount'] == 7.87
    assert result['execution'] == {'mode': 'simulation', 'scenario': scenario}
    assert result['agent_results']['rider']['status'] == expected_status
    assert result['agent_results']['rider']['attempts'] == attempts
    assert all(v['is_simulated'] for v in result['agent_results'].values())
    actors = {e['actor'] for e in snapshot['events']}
    assert {'Rider Advocate', 'Driver Advocate', 'Judge'} <= actors
    assert any(e['kind'] == 'tool' and e['status'] == 'completed' for e in snapshot['events'])
    assert [e['seq'] for e in snapshot['events']] == list(range(1, snapshot['next_seq'] + 1))
    assert {p['id'] for p in result['policy_catalog']} == set(result['ruling']['matched_policy_ids'])
    assert all(p['version'] == result['policy_version'] for p in result['policy_catalog'])
    assert client.get(f'/api/runs/{run_id}?after={snapshot["next_seq"]}').json()['events'] == []


def test_run_api_rejects_invalid_requests(client):
    assert client.post('/api/runs', json={'case_id': 'not-found'}).status_code == 404
    for payload in [{'case_id': 12}, {'case_id': 'DISP-002', 'scenario': 'real'},
                    {'case_id': 'DISP-002', 'api_key': 'bad'}]:
        assert client.post('/api/runs', json=payload).status_code == 422
    assert client.get('/api/runs/unknown').status_code == 404
    assert client.get('/api/runs/unknown?after=-1').status_code == 422


def test_real_http_poll_observes_agent_before_completion(client, monkeypatch):
    from backend.core.simulation import SimulationProvider
    entered, release = Event(), Event()
    original = SimulationProvider.complete_structured
    def blocked(self, *args, **kwargs):
        entered.set()
        assert release.wait(3)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(SimulationProvider, 'complete_structured', blocked)
    response = client.post('/api/runs', json={'case_id': 'DISP-002'})
    assert response.status_code == 202
    run_id = response.json()['run_id']
    try:
        assert entered.wait(2)
        before = client.get('/api/runs/' + run_id).json()
        assert before['status'] == 'running' and before['result'] is None
        assert any(e['actor'] == 'Rider Advocate' for e in before['events'])
    finally:
        release.set()
    assert finish(client, run_id)['result']['ruling']['amount'] == 0


def test_policy_missing_cannot_authorize_refund(disputes, config):
    from backend.core.evidence import analyze_evidence
    from backend.core.policy import apply_policy
    ruling = apply_policy(analyze_evidence(disputes[0]), [], config)
    assert ruling.escalate is True
    assert ruling.action == 'escalate'
    assert ruling.matched_policy_ids == []


def test_missing_lateness_cannot_uphold_no_show(policies, config):
    from backend.core.evidence import analyze_evidence
    from backend.core.policy import apply_policy
    case = {'category': 'no_show', 'fare': {'cancellation_fee': 5},
            'gps': {'driver_arrival': {'arrived': True, 'wait_time_min': 8}},
            'chat_log': [{'from': 'driver', 'text': 'I am at pickup'}]}
    evidence = analyze_evidence(case)
    result = apply_policy(evidence, policies, config)
    assert evidence.driver_late_min is None
    assert result.escalate is True and result.action == 'insufficient_evidence'
