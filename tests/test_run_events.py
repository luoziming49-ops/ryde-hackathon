from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from backend.core.events import RunRecorder, RunStore, RunCapacityError
from backend.core.tools import CaseTools


def test_recorder_parallel_sequences_and_snapshot_isolation():
    recorder = RunRecorder('sample-run')
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda n: recorder.emit('Test', 'step', 'completed', output_summary=str(n)), range(30)))
    snapshot = recorder.snapshot()
    assert [e['seq'] for e in snapshot['events']] == list(range(1, 31))
    assert len(recorder.snapshot(after=25)['events']) == 5
    snapshot['events'][0]['output_summary'] = 'changed'
    assert recorder.snapshot()['events'][0]['output_summary'] != 'changed'


def test_run_exposes_event_before_work_completes_and_limits_concurrency():
    entered, release = Event(), Event()
    def work(recorder):
        recorder.emit('Rider Advocate', 'agent', 'running')
        entered.set()
        assert release.wait(3)
        return {'answer': 7.87}
    store = RunStore(max_runs=2, max_workers=1)
    try:
        run_id = store.start(work)
        assert entered.wait(2)
        snapshot = store.get(run_id)
        assert snapshot['status'] == 'running' and snapshot['result'] is None
        assert any(e['actor'] == 'Rider Advocate' for e in snapshot['events'])
        with pytest.raises(RunCapacityError): store.start(work)
        release.set()
        store.close()
        assert store.get(run_id)['status'] == 'completed'
        assert store.get(run_id)['result'] == {'answer': 7.87}
    finally:
        release.set()
        store.close()


def test_store_error_is_fixed_and_completed_runs_are_evicted():
    store = RunStore(max_runs=1)
    def broken(recorder): raise RuntimeError('secret from network')
    failed = store.start(broken)
    store.wait(failed, timeout=2)
    snapshot = store.get(failed)
    assert snapshot['status'] == 'failed' and snapshot['error_code'] == 'run_failed'
    assert 'secret' not in str(snapshot)
    done = store.start(lambda r: {'value': 1})
    store.wait(done, timeout=2)
    with pytest.raises(KeyError): store.get(failed)
    assert store.get(done)['result'] == {'value': 1}
    store.close()


def test_case_tool_reads_only_whitelisted_local_fields_and_records_result():
    recorder = RunRecorder('tools')
    original = {'case_id': 'c1', 'fare': {'base_fare': 3}, 'secret': 'never'}
    tools = CaseTools(original, recorder)
    fare = tools.read('fare')
    fare['base_fare'] = 9
    assert original['fare']['base_fare'] == 3
    with pytest.raises(ValueError): tools.read('secret')
    events = recorder.snapshot()['events']
    assert events[0]['status'] == 'running'
    assert events[1]['status'] == 'completed' and events[1]['parent_id'] == events[0]['seq']
    assert 'never' not in str(events)
    assert events[1]['duration_ms'] >= 0
