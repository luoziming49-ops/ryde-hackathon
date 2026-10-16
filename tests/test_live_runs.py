"""Live runs are explicit, configured and distinguish sample data from model mode."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.llm import LLMProvider
from backend.core.simulation import SimulationProvider


def enable(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','')
    monkeypatch.setenv('LLM_API_KEY','local-test-key')
    monkeypatch.setenv('LLM_BASE_URL','https://example.invalid/v1')
    monkeypatch.setenv('LLM_CONFIRMED_BASE_URL','https://example.invalid/v1')
    monkeypatch.setenv('LLM_MODEL','test-model')
    monkeypatch.setenv('LLM_LIVE_ENABLED','true')


def test_live_disabled_without_opt_in(client):
    assert client.get('/api/health').json()['live_enabled'] is False
    assert client.post('/api/live-runs',json={'case_id':'DISP-002'}).status_code==503


def test_live_requires_exact_confirmed_destination(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setenv('LLM_CONFIRMED_BASE_URL','https://different.invalid/v1')
    with TestClient(app) as client:
        assert client.get('/api/health').json()['live_enabled'] is False
        assert client.post('/api/live-runs',json={'case_id':'DISP-002'}).status_code==503


def test_live_run_preserves_sample_label_and_real_mode(monkeypatch):
    enable(monkeypatch)
    fake=SimulationProvider('success')
    monkeypatch.setattr(LLMProvider,'_request',lambda self,*a,**kw:fake._request(*a,**kw))
    with TestClient(app) as client:
        health=client.get('/api/health').json()
        assert health['live_enabled'] is True and health['live_model']=='test-model'
        response=client.post('/api/live-runs',json={'case_id':'DEMO-ORAL-NOT-AGREED'})
        assert response.status_code==202
        rid=response.json()['run_id'];app.state.runs.wait(rid,timeout=3)
        snapshot=client.get('/api/runs/'+rid).json();result=snapshot['result']
        assert result['execution']['mode']=='live'
        assert result['execution']['http_attempts']==3
        assert result['execution']['request_limit']==6
        assert result['ruling']['amount']==7.87
        assert all(row['is_simulated'] for row in result['evidence_catalog'])
        assert all(row['mode']=='llm' and row['status']=='ok' and not row['is_simulated'] for row in result['agent_results'].values())
        assert snapshot['events'][0]['mode']=='live'
        assert 'simulation' not in snapshot['events'][0]['output_summary'].lower()
        assert client.get('/api/health').json()['last_call_ok'] is True
        assert 'local-test-key' not in str(result)


def test_live_rejects_external_origin_and_extra_request_fields(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setattr('backend.core.llm.requests.post',lambda *a,**k:pytest.fail('Network forbidden'))
    with TestClient(app) as client:
        assert client.post('/api/live-runs',headers={'Origin':'https://foreign.invalid'},json={'case_id':'DISP-002'}).status_code==403
        for data in [{'case_id':'DISP-002','api_key':'bad'},{'case_id':'DISP-002','scenario':'success'},{'case_id':42}]:
            assert client.post('/api/live-runs',json=data).status_code==422
        assert client.post('/api/live-runs',json={'case_id':'missing'}).status_code==404


def test_legacy_resolve_remains_offline_even_with_configured_key(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setenv('LLM_LIVE_ENABLED', 'false')
    calls = []
    def unexpected(*a, **kw):
        calls.append(1)
        raise RuntimeError('Legacy endpoint must not spend')
    monkeypatch.setattr('backend.core.llm.requests.post', unexpected)
    with TestClient(app) as client:
        response = client.post('/api/resolve', headers={'Origin': 'https://foreign.invalid'}, json={'case_id': 'DISP-002'})
        assert response.status_code == 200
        assert calls == []
        assert all(row['mode'] == 'fallback' and row['attempts'] == 0 for row in response.json()['agent_results'].values())


def test_bad_live_config_keeps_health_and_simulation_usable(monkeypatch):
    enable(monkeypatch)
    monkeypatch.setenv('LLM_JSON_MODE', 'invalid')
    monkeypatch.setattr('backend.core.llm._provider', None)
    with TestClient(app) as client:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['live_enabled'] is False
        assert response.json()['last_error'] == 'invalid_configuration'
        response = client.post('/api/runs', json={'case_id': 'DISP-002'})
        assert response.status_code == 202
        app.state.runs.wait(response.json()['run_id'], timeout=3)
