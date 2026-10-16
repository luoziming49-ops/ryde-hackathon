"""Run an offline, frozen expectation matrix: python -m backend.evaluate."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from .adapters.official_ticket import normalize_official_ticket, is_official_ticket
from .agents.orchestrator import DisputeOrchestrator
from .core.simulation import SimulationProvider
from .schemas import Dispute, dump_dispute

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'sample_data'


def evaluate(golden_path=None):
    golden = json.loads(Path(golden_path or DATA/'evaluation/golden.json').read_text())
    samples = {d['case_id']: d for d in json.loads((DATA/'disputes.json').read_text())}
    for path in (DATA/'official').glob('*.json'):
        raw = json.loads(path.read_text())
        samples[raw['dispute_ticket']['dispute_id']] = raw
    policies = json.loads((DATA/'policies.json').read_text())
    precedents = json.loads((DATA/'precedents.json').read_text())['precedents']
    results = []
    for spec in golden['cases']:
        started = perf_counter()
        case = deepcopy(samples[spec['case_id']])
        for path, value in spec.get('set_paths', {}).items():
            target = case
            parts = path.split('.')
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value
        scenario = spec.get('scenario', 'success')
        try:
            case = normalize_official_ticket(case) if is_official_ticket(case) else dump_dispute(Dispute.model_validate(case))
            chosen_policies = [] if spec.get('policy_mode') == 'empty' else policies['policies']
            engine = DisputeOrchestrator(chosen_policies, precedents, policies.get('config', {}))
            result = engine.resolve(case, is_simulated=True, provider=SimulationProvider(scenario))
            rider = result['agent_results']['rider']
            actual = {'status': 200, 'action': result['ruling']['action'], 'amount': result['ruling']['amount'],
                      'escalated': result['ruling']['escalated'], 'rider_status': rider['status'],
                      'rider_attempts': rider['attempts']}
        except ValidationError:
            actual = {'status': 422}
        expected = spec['expected']
        mismatches = [key for key, value in expected.items() if actual.get(key) != value]
        results.append({'id': spec['id'], 'case_id': spec['case_id'], 'scenario': scenario,
                        'expected': expected, 'actual': actual, 'passed': not mismatches,
                        'mismatches': mismatches, 'duration_ms': round((perf_counter()-started)*1000, 3),
                        'basis': spec.get('basis', '')})
    passed = sum(row['passed'] for row in results)
    return {'generated_at': datetime.now(timezone.utc).isoformat(), 'mode': 'simulation',
            'golden_version': golden.get('version'), 'scope': 'Fixed offline consistency cases; not model accuracy.',
            'total': len(results), 'passed': passed, 'failed': len(results)-passed, 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    for row in report['results']:
        print(('PASS' if row['passed'] else 'FAIL') + ' ' + row['id'])
    print(f"{report['passed']}/{report['total']} passed; {report['failed']} failed. SIMULATION ONLY.")
    raise SystemExit(bool(report['failed']))
