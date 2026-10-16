from backend.evaluate import evaluate


def test_frozen_matrix_runs_without_external_calls(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY', 'not-for-network')
    monkeypatch.setattr('backend.core.llm.requests.post', lambda *a, **k: (_ for _ in ()).throw(AssertionError('No network')))
    report = evaluate()
    assert report['total'] >= 24
    assert report['failed'] == 0
    assert report['passed'] == report['total']
    assert report['mode'] == 'simulation'
    assert {'success', 'rider_rejected', 'retry_success', 'provider_error'} <= {row['scenario'] for row in report['results']}
    assert any(row['actual'].get('status') == 422 for row in report['results'])
    assert any(row['actual'].get('action') == 'insufficient_evidence' for row in report['results'])


def test_wrong_golden_expectation_is_reported_not_rewritten(tmp_path):
    import json
    path = tmp_path/'bad.json'
    path.write_text(json.dumps({'cases': [{'id': 'bad-golden', 'case_id': 'RYDE-2026-0001',
        'scenario': 'success',
        'set_paths': {'rider.route_consent': 'not_agreed', 'driver.route_consent': 'not_agreed'},
        'expected': {'action': 'full_refund', 'amount': 999}}]}))
    report = evaluate(path)
    assert report['failed'] == 1
    assert report['results'][0]['expected']['amount'] == 999
    assert report['results'][0]['actual']['amount'] == 7.87
