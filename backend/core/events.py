"""Bounded, single-process demo runs; records actual execution, not model thought."""

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4


class RunCapacityError(RuntimeError):
    pass


class RunRecorder:
    def __init__(self, run_id=None):
        self.run_id = run_id or uuid4().hex
        self._lock = RLock()
        self._events = []
        self._status = 'running'
        self._result = None
        self._error_code = None

    def emit(self, actor, kind, status, *, parent_id=None, duration_ms=None,
             input_summary='', output_summary='', evidence_ids=None,
             mode='deterministic', meta=None):
        with self._lock:
            event = dict(run_id=self.run_id, seq=len(self._events) + 1,
                         parent_id=parent_id, actor=actor, kind=kind, status=status,
                         started_at=datetime.now(timezone.utc).isoformat(),
                         duration_ms=duration_ms, input_summary=input_summary[:1000],
                         output_summary=output_summary[:4000], evidence_ids=evidence_ids or [],
                         mode=mode, meta=meta or {})
            self._events.append(deepcopy(event))
            return event

    def message(self, message):
        meta = message.meta
        llm = meta.get('llm') or {}
        mode = 'simulation' if llm.get('is_simulated') else llm.get('mode', 'deterministic')
        self.emit(message.agent, message.role, 'completed', output_summary=message.content,
                  evidence_ids=meta.get('evidence_ids', []), mode=mode, meta=meta)

    def finish(self, result=None, error_code=None):
        with self._lock:
            self._status = 'failed' if error_code else 'completed'
            self._result = deepcopy(result)
            self._error_code = error_code
            self.emit('Orchestrator', 'run', self._status,
                      output_summary=error_code or 'Run completed; recommendation only. No payment executed.')

    def snapshot(self, after=0):
        with self._lock:
            return deepcopy(dict(run_id=self.run_id, status=self._status,
                                 events=self._events[after:], next_seq=len(self._events),
                                 result=self._result, error_code=self._error_code))


class RunStore:
    """At most max_workers running and max_runs retained; no unbounded work queue."""
    def __init__(self, max_runs=50, max_workers=2):
        self.max_runs = max_runs
        self.max_workers = max_workers
        self._lock = RLock()
        self._runs = OrderedDict()
        self._futures = {}
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix='ryde-demo')

    def start(self, work, *, mode='simulation'):
        with self._lock:
            if sum(r.snapshot()['status'] == 'running' for r in self._runs.values()) >= self.max_workers:
                raise RunCapacityError('run_capacity')
            while len(self._runs) >= self.max_runs:
                old = next((key for key, r in self._runs.items() if r.snapshot()['status'] != 'running'), None)
                if old is None:
                    raise RunCapacityError('run_capacity')
                self._runs.pop(old)
                self._futures.pop(old, None)
            recorder = RunRecorder()
            recorder.emit('Orchestrator', 'run', 'running', mode=mode,
                          output_summary='Live API run started; sample evidence.' if mode == 'live'
                          else 'Local simulation started.')
            self._runs[recorder.run_id] = recorder
            def execute():
                try:
                    recorder.finish(work(recorder))
                except Exception:
                    recorder.finish(error_code='run_failed')
            self._futures[recorder.run_id] = self._pool.submit(execute)
            return recorder.run_id

    def get(self, run_id, after=0):
        with self._lock:
            return self._runs[run_id].snapshot(after)

    def wait(self, run_id, timeout=None):
        with self._lock:
            future = self._futures[run_id]
        future.result(timeout=timeout)

    def close(self):
        self._pool.shutdown(wait=True)
