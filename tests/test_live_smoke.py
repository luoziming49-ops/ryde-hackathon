"""The live smoke command is bounded and never counts fallback as success."""
import json

import pytest

from backend.core.llm import LLMConfig, LLMProvider
from backend.core.simulation import SimulationProvider
from backend.live_smoke import run_smoke

URL = 'https://provider.example.invalid/v1'


def config(url=URL):
    return LLMConfig(url, 'private-fixture-key', 'test-model')


def test_confirmed_destination_is_required_before_any_request(monkeypatch):
    monkeypatch.setattr('backend.core.llm.requests.post', lambda *a, **k: pytest.fail('Unexpected HTTP'))
    for cfg, target in [(config(), 'https://other.example.invalid/v1'), (config('http://provider.example.invalid/v1'), 'http://provider.example.invalid/v1'), (config(URL+'?key=private'), URL+'?key=private')]:
        with pytest.raises(ValueError, match='invalid_destination|destination_mismatch'):
            run_smoke('RYDE-2026-0001', cfg, target)
    with pytest.raises(ValueError, match='missing_credentials'):
        run_smoke('RYDE-2026-0001', LLMConfig(URL, '', 'test-model'), URL)


def test_real_success_requires_all_agents_and_expected_ruling(monkeypatch):
    fake = SimulationProvider('success')
    monkeypatch.setattr(LLMProvider, '_request', lambda self, *a, **k: fake._request(*a, **k))
    report = run_smoke('RYDE-2026-0001', config(), URL)
    assert report['passed'] is True
    assert report['http_attempts'] == 3
    assert report['actual'] == {'action': 'partial_refund', 'amount': 7.87}
    assert report['usage_complete'] is False and report['usage'] is None
    assert report['cost'] is None
    assert 'private-fixture-key' not in json.dumps(report)


def test_transport_error_stops_further_requests_and_is_not_success(monkeypatch):
    calls=[]
    def boom(*a, **k):
        calls.append(1)
        raise RuntimeError('private-fixture-key: remote body')
    monkeypatch.setattr(LLMProvider, '_request', boom)
    report = run_smoke('DISP-002', config(), URL)
    assert report['passed'] is False
    assert len(calls)==report['http_attempts']==1
    assert report['checks']['all_agents_live'] is False
    assert 'private-fixture-key' not in json.dumps(report)
    assert 'remote body' not in json.dumps(report)


def test_rejected_drafts_are_bounded_and_failure_is_reported(monkeypatch):
    calls=[]
    def bad(*a, **k):
        calls.append(1)
        return 'invalid json'
    monkeypatch.setattr(LLMProvider, '_request', bad)
    report=run_smoke('RYDE-2026-0002',config(),URL)
    assert len(calls)==report['http_attempts']==6
    assert report['passed'] is False
    assert report['actual']['amount']==5
    assert all(x['status']=='rejected' for x in report['agents'].values())


def test_unknown_case_and_excessive_budget_never_call_network(monkeypatch):
    monkeypatch.setattr('backend.core.llm.requests.post', lambda *a, **k: pytest.fail('Unexpected HTTP'))
    with pytest.raises(ValueError, match='unknown_case'):
        run_smoke('not-a-sample',config(),URL)
    for limit in [0,7,True]:
        with pytest.raises(ValueError,match='invalid_request_limit'):
            run_smoke('DISP-002',config(),URL,request_limit=limit)

@pytest.mark.parametrize('messages,max_tokens', [
    ([{'role': 'user', 'content': '界' * 20001}], 1800),
    ([{'role': 'user', 'content': 'sample'}], 1801),
])
def test_live_payload_limits_reject_before_transport(monkeypatch, messages, max_tokens):
    from backend.live_smoke import BoundedLiveProvider
    monkeypatch.setattr(LLMProvider, '_request', lambda *a, **k: pytest.fail('Unexpected transport'))
    provider = BoundedLiveProvider(config())
    with pytest.raises(RuntimeError, match='live_token_limit'):
        provider._request(messages, temperature=0.1, max_tokens=max_tokens)
    assert provider.http_attempts == 0
