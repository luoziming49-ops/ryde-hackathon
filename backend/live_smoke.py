"""Bounded real-provider verification on frozen sample expectations.

Explicit --live and --confirm-base-url are required before any model requests.
Only sanitized metrics are reported; case data remains labelled as samples.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

from .adapters.official_ticket import normalize_official_ticket
from .agents.orchestrator import DisputeOrchestrator
from .core.config import load_dotenv
from .core.llm import LLMConfig, LLMProvider, _config_from_env
from .schemas import Dispute, dump_dispute

DATA = Path(__file__).resolve().parent.parent / 'sample_data'


class BoundedLiveProvider(LLMProvider):
    """One instance per sequential run; stop network after first transport error."""
    def __init__(self, config, request_limit=6):
        super().__init__(config)
        self.request_limit = request_limit
        self.http_attempts = 0
        self.transport_failed = False

    def _request(self, *args, **kwargs):
        if self.transport_failed or self.http_attempts >= self.request_limit:
            raise RuntimeError('live_request_limit')
        messages = args[0] if args else kwargs.get('messages', [])
        if (sum(len(item['content'].encode('utf-8')) for item in messages) > 60000
                or kwargs.get('max_tokens', 0) > 1800):
            raise RuntimeError('live_token_limit')
        self.http_attempts += 1
        try:
            return super()._request(*args, **kwargs)
        except Exception:
            self.transport_failed = True
            raise


def validate_destination(config, confirmed_base_url):
    if config is None or not config.api_key:
        raise ValueError('missing_credentials')
    base = config.base_url.rstrip('/')
    url = urlsplit(base)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment):
        raise ValueError('invalid_destination')
    if base != confirmed_base_url.rstrip('/'):
        raise ValueError('destination_mismatch')
    return base


def _sample(case_id):
    for case in json.loads((DATA / 'disputes.json').read_text()):
        if case['case_id'] == case_id:
            return dump_dispute(Dispute.model_validate(case))
    for path in sorted((DATA / 'official').glob('*.json')):
        raw = json.loads(path.read_text())
        if raw['dispute_ticket']['dispute_id'] == case_id:
            return normalize_official_ticket(raw)
    raise ValueError('unknown_case')


def run_smoke(case_id: str, config: LLMConfig, confirmed_base_url: str, *, request_limit=6):
    base = validate_destination(config, confirmed_base_url)
    if type(request_limit) is not int or not 1 <= request_limit <= 6:
        raise ValueError('invalid_request_limit')
    case = _sample(case_id)
    golden = json.loads((DATA / 'evaluation/golden.json').read_text())
    expected = next(row['expected'] for row in golden['cases'] if row['id'] == case_id + '-success')
    policy = json.loads((DATA / 'policies.json').read_text())
    precedents = json.loads((DATA / 'precedents.json').read_text())['precedents']
    provider = BoundedLiveProvider(config, request_limit)
    engine = DisputeOrchestrator(policy['policies'], precedents, policy.get('config', {}))
    started = perf_counter()
    result = engine.resolve(case, is_simulated=True, provider=provider)
    agents = result['agent_results']
    actual = {field: result['ruling'][field] for field in ('action', 'amount')}
    checks = {
        'all_agents_live': all(row['mode'] == 'llm' and row['status'] == 'ok'
                               and not row['is_simulated'] for row in agents.values()),
        'ruling_matches_expected': all(actual[field] == expected[field] for field in actual),
        'guard_approved': result['ruling']['guard']['status'] == 'approved',
    }
    usage = {}
    for row in agents.values():
        for key, value in (row.get('usage') or {}).items():
            usage[key] = usage.get(key, 0) + value
    return {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'mode': 'live', 'evidence_mode': 'sample', 'payment_executed': False,
        'case_id': case_id, 'model': config.model, 'provider_base_url': base,
        'passed': all(checks.values()), 'checks': checks,
        'http_attempts': provider.http_attempts, 'request_limit': request_limit,
        'duration_ms': round((perf_counter()-started)*1000),
        'usage': usage or None, 'usage_complete': all(row.get('usage_complete', False) for row in agents.values()),
        'cost': None, 'cost_note': 'Token usage is provider-reported; no invoice amount is inferred.',
        'agents': agents, 'actual': actual,
        'expected': {field: expected[field] for field in actual},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', help='Send real billable model requests.')
    parser.add_argument('--confirm-base-url', required=True)
    parser.add_argument('--case', default='RYDE-2026-0001')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.live:
        parser.error('--live is required; no model requests sent')
    load_dotenv()
    try:
        report = run_smoke(args.case, _config_from_env(), args.confirm_base_url)
    except ValueError as exc:
        # Only allow fixed local diagnostics; never stringify remote errors.
        code = str(exc)
        safe = {'missing_credentials', 'invalid_destination', 'destination_mismatch', 'unknown_case', 'invalid_request_limit'}
        print(json.dumps({'passed': False, 'error': code if code in safe else 'invalid_configuration'}))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
