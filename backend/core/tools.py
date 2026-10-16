"""Read-only tools over a single supplied case, with actual start/end events."""

from copy import deepcopy
from time import perf_counter


class CaseTools:
    FIELDS = ('gps', 'chat_log', 'fare', 'rider', 'driver', 'trip')

    def __init__(self, dispute, recorder):
        self.dispute = dispute
        self.recorder = recorder

    def call(self, name, action, summary):
        start = self.recorder.emit('Evidence Collection', 'tool', 'running', input_summary=name)
        begun = perf_counter()
        try:
            result = action()
        except Exception:
            self.recorder.emit('Evidence Collection', 'tool', 'failed', parent_id=start['seq'],
                               input_summary=name, output_summary='local_tool_failed',
                               duration_ms=round((perf_counter() - begun) * 1000, 3))
            raise
        self.recorder.emit('Evidence Collection', 'tool', 'completed', parent_id=start['seq'],
                           input_summary=name, output_summary=summary(result),
                           duration_ms=round((perf_counter() - begun) * 1000, 3))
        return result

    def read(self, field):
        if field not in self.FIELDS:
            raise ValueError('field_not_allowed')
        return self.call('case.read.' + field, lambda: deepcopy(self.dispute.get(field)),
                         lambda value: 'Missing' if value is None else
                         f'{len(value)} supplied entries' if isinstance(value, (dict, list)) else 'Value read')

    def materialize(self):
        case = deepcopy(self.dispute)
        for field in self.FIELDS:
            value = self.read(field)
            if value is not None:
                case[field] = value
        return case
