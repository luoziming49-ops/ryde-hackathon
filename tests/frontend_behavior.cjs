const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() {
    this.innerHTML = ''; this.textContent = ''; this.disabled = false;
    this.listeners = {}; this.children = []; this.className = ''; this.value = 'success'; this.hidden = false; this.dataset = {}; this.attributes = {};
    this.classList = { add() {}, remove() {}, toggle() {} };
  }
  focus() { document.activeElement = this; }
  setAttribute(key, value) { this.attributes[key] = value; }
  click() { return this.listeners.click?.({target: this}); }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  appendChild(child) { this.children.push(child); }
  querySelector() { return null; }
  querySelectorAll() { return []; }
}

const elements = new Map();
const element = selector => {
  if (!elements.has(selector)) elements.set(selector, new Element());
  return elements.get(selector);
};
const createdElements = [];
const document = {
  querySelector: element, querySelectorAll: () => [],
  createElement: () => { const el = new Element(); createdElements.push(el); return el; }, activeElement: null, listeners: {},
  addEventListener(type, handler) { this.listeners[type] = handler; },
};
const downloads = [];
const urls = {createObjectURL(blob) { downloads.push(blob); return 'blob:local'; }, revokeObjectURL() {}};
const context = vm.createContext({ document, console, setTimeout: fn => fn(), clearTimeout: () => {}, AbortController, Blob, URL: urls, fetch: async () => {
  throw new Error('Unexpected network request');
}});
const html = fs.readFileSync('frontend/index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
// Avoid startup I/O; tests call the production functions and actual click handler.
vm.runInContext(script.replace(/\ninit\(\);\s*$/, ''), context);
const run = code => vm.runInContext(code, context);
const setCase = data => { context.fixture = data; run('selectedData = fixture; selected = "test";'); };
const panel = () => element('#evidencePanel').innerHTML;
const rowValue = (markup, label) => {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = markup.match(new RegExp(`<span class="k">${escaped}</span><span class="v">([^<]*)</span>`));
  assert.ok(match, `Missing row: ${label}`);
  return match[1];
};
const scenario = process.argv[2];
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const agentResult = (overrides = {}) => ({mode: 'llm', status: 'ok', model: 'test-model',
  prompt_version: 'advocate.v1', latency_ms: 24, error_code: null, attempts: 1,
  attempt_errors: [], ...overrides});
const rulingResponse = (overrides = {}) => ({trace: [], duration_ms: 30,
  ruling: {action: 'partial_refund', amount: 7.87, currency: 'SGD', confidence: .96,
    reasoning: 'Partial refund of SGD 7.87.', escalated: false,
    reasoning_source: 'verified_template',
    guard: {status: 'approved', reasons: [], final_action: 'partial_refund', final_amount: 7.87,
      policy_version: 'policy.v1', evidence_ids: ['e1', 'e2']}}, ...overrides});
const renderResponse = response => { context.responseFixture = response; run('renderRuling(responseFixture)'); };
const agentRow = party => {
  const markup = element('#agentResults').innerHTML;
  const match = markup.match(new RegExp(`<div[^>]*data-agent="${party}"[^>]*>([\\s\\S]*?)<\\/div>`));
  assert.ok(match, `Missing ${party} result`);
  return match[1];
};

async function liveTest(name) {
  const ok = data => ({ok: true, json: async () => data});
  const health = {state: 'configured', model: 'deepseek-chat', live_enabled: true, live_model: 'deepseek-chat'};
  const switchMode = async mode => {
    element('#modeSelect').value = mode;
    assert.equal(typeof element('#modeSelect').listeners.change, 'function', 'mode selection must handle changes');
    await element('#modeSelect').listeners.change({target: element('#modeSelect')});
  };
  const enableLive = async () => { setCase({}); context.healthFixture = health; run('renderHealth(healthFixture)'); await switchMode('live'); };
  const agents = {rider: agentResult(), driver: agentResult(), judge: agentResult()};
  const result = rulingResponse({case_id: 'test', run_id: 'live-one', execution: {mode: 'live', scenario: null}, agent_results: agents,
    evidence_catalog: [{id: 'e1', is_simulated: true, source: 'sample', text: 'Sample trip'}]});
  const completed = {run_id: 'live-one', status: 'completed', events: [], next_seq: 0, result};
  if (name === 'live_availability') {
    setCase({});
    run('renderHealth({state: "ok", model: "m"})');
    assert.equal(element('#liveModeOption').disabled, true, 'legacy health must not permit live requests');
    assert.equal(element('#modeSelect').value, 'simulation');
    run('renderHealth({state: "configured", live_enabled: "true"})');
    assert.equal(element('#liveModeOption').disabled, true);
    context.healthFixture = health; run('renderHealth(healthFixture)');
    assert.equal(element('#liveModeOption').disabled, false);
    assert.equal(element('#modeSelect').value, 'simulation', 'configuration must not auto-switch mode');
    assert.equal(element('#resolveBtn').textContent, 'Run simulation');
    await switchMode('live');
    assert.match(element('#modeTitle').textContent, /live API/i);
    assert.match(element('#modeDescription').textContent, /sample.*model.*usage/i);
    assert.match(element('#modeDescription').textContent, /no payment/i);
    assert.equal(element('#scenarioControl').hidden, true);
    assert.equal(element('#scenarioSelect').disabled, true);
    assert.equal(element('#resolveBtn').textContent, 'Run live API');
    await switchMode('simulation');
    assert.equal(element('#scenarioControl').hidden, false);
    assert.match(element('#modeDescription').textContent, /no external model calls/i);
  } else if (name === 'live_startup_health_failure') {
    context.fetch = async url => url === '/api/health'
      ? {ok: false, status: 503, json: async () => ({...health, state: 'ok'})} : ok([]);
    await run('init()');
    assert.equal(element('#liveModeOption').disabled, true, 'an HTTP failure cannot authorize live requests');
    assert.match(element('#llmText').textContent, /unavailable|unreachable/i);
  } else if (name === 'live_unavailable') {
    setCase({}); run('renderHealth(null)');
    await switchMode('live');
    assert.equal(element('#modeSelect').value, 'simulation');
    await enableLive(); run('renderHealth(null)');
    assert.equal(element('#resolveBtn').disabled, true);
    assert.match(element('#modeAvailability').textContent, /unavailable/i);
    let calls = 0; context.fetch = async () => {calls++; throw new Error('Must not call');};
    await element('#resolveBtn').click(); assert.equal(calls, 0);
    await switchMode('simulation'); assert.equal(element('#resolveBtn').disabled, false);
  } else if (name === 'live_usage') {
    renderResponse(rulingResponse({agent_results: {
      rider: agentResult({usage: {prompt_tokens: 11, completion_tokens: 0, total_tokens: 11}, usage_complete: true}),
      driver: agentResult({usage: {prompt_tokens: 3, completion_tokens: 2, total_tokens: 5}, usage_complete: false}),
      judge: agentResult({usage: null, usage_complete: false})}}));
    assert.match(agentRow('rider'), /Tokens.*11.*0.*11/);
    assert.doesNotMatch(agentRow('rider'), /partial|unavailable/i);
    assert.match(agentRow('driver'), /Tokens.*partial.*3.*2.*5/i);
    assert.match(agentRow('judge'), /Tokens.*unavailable/i);
    renderResponse(rulingResponse({agent_results: {rider: agentResult({usage: {prompt_tokens: 4}, usage_complete: true}),
      driver: agentResult({usage: {total_tokens: '<img>'}, usage_complete: true})}}));
    assert.match(agentRow('rider'), /Tokens.*partial.*4/i);
    assert.doesNotMatch(agentRow('rider'), /total.*4/);
    assert.match(agentRow('driver'), /Tokens.*unavailable/i);
    assert.doesNotMatch(agentRow('driver'), /<img/);
  } else if (name === 'live_switch_loading_case') {
    context.healthFixture = health; run('renderHealth(healthFixture)');
    let release, loads = 0;
    const oldCase = new Promise(resolve => {release = resolve;});
    context.fetch = async url => {
      assert.equal(url, '/api/disputes/test');
      return ++loads === 1 ? oldCase : ok({case_id: 'test', trip: {pickup: {name: 'Current case'}}});
    };
    const loading = run("selectDispute('test')");
    await switchMode('live');
    release(ok({case_id: 'test', trip: {pickup: {name: 'Stale case'}}})); await loading;
    assert.equal(element('#resolveBtn').disabled, false);
    assert.equal(element('#resolveBtn').textContent, 'Run live API');
    assert.match(panel(), /Current case/); assert.doesNotMatch(panel(), /Stale case/);
  } else if (name === 'live_stale_simulation') {
    setCase({}); context.healthFixture = health; run('renderHealth(healthFixture)');
    let release;
    const pending = new Promise(resolve => {release = resolve;});
    context.fetch = async url => {
      assert.equal(url, '/api/runs'); return pending;
    };
    const old = element('#resolveBtn').click(); await switchMode('live');
    release(ok({run_id: 'simulation-old', status: 'running'})); await old;
    assert.match(element('#modeTitle').textContent, /live API/i);
    assert.equal(element('#downloadBtn').disabled, true);
    assert.equal(run('currentResult'), null);
    assert.equal(element('#resolveBtn').textContent, 'Run live API');
  } else if (name.startsWith('live_stale_')) {
    await enableLive(); let release, requests = [];
    const pending = new Promise(resolve => {release = resolve;});
    context.fetch = async (url, options) => {
      requests.push({url, options});
      if (url === '/api/live-runs') return name === 'live_stale_post' ? pending : ok({run_id: 'live-one', status: 'running'});
      if (url.startsWith('/api/runs/live-one?')) return name === 'live_stale_poll' ? pending : ok(completed);
      if (url === '/api/health') return pending;
      throw new Error('Unexpected ' + url);
    };
    const old = element('#resolveBtn').click(); await new Promise(resolve => setImmediate(resolve));
    await switchMode('simulation'); element('#resolveBtn').disabled = true;
    assert.equal(requests[0].options.signal.aborted, true);
    release(ok(name === 'live_stale_post' ? {run_id: 'live-one', status: 'running'} : name === 'live_stale_poll' ? completed : {state: 'no_key', live_enabled: false}));
    await old;
    assert.equal(element('#resolveBtn').disabled, true, 'old finally must not alter current mode state');
    assert.equal(element('#downloadBtn').disabled, true);
    assert.equal(run('currentResult'), null);
    assert.doesNotMatch(element('#ruling').innerHTML, /Partial Refund/);
    assert.match(element('#modeTitle').textContent, /simulation/i);
    if (name === 'live_stale_health') assert.equal(element('#liveModeOption').disabled, false);
  } else {
    await enableLive(); let starts = 0;
    if (name === 'live_fallback') result.agent_results.driver = agentResult({mode: 'fallback', status: 'error', error_code: 'timeout'});
    if (name === 'live_unknown_agents') delete result.agent_results;
    if (name === 'live_guard_rejected') result.ruling.guard.status = 'rejected';
    if (name === 'live_wrong_mode') result.execution.mode = 'simulation';
    context.fetch = async (url, options) => {
      if (url === '/api/live-runs') {
        starts++;
        assert.deepEqual(JSON.parse(options.body), {case_id: 'test'}, 'live requests must omit simulation scenario');
        return ok({run_id: 'live-one', status: 'running'});
      }
      if (url.startsWith('/api/runs/live-one?')) {
        if (name === 'live_failure_retry' && starts === 1) return ok({run_id: 'live-one', status: 'failed', events: [], next_seq: 0, error_code: 'provider_error'});
        return ok({...completed, events: [{seq: 1, actor: 'Judge', kind: 'agent', status: 'completed', input_summary: '', output_summary: 'Checked', mode: 'live', duration_ms: 10}], next_seq: 1});
      }
      if (url === '/api/health') return ok({...health, state: 'ok'});
      throw new Error('Wrong endpoint ' + url);
    };
    await element('#resolveBtn').click();
    if (name === 'live_failure_retry') {
      assert.match(element('#runStatus').textContent, /live API.*failed.*retry/i);
      assert.equal(element('#downloadBtn').disabled, true);
      assert.equal(element('#resolveBtn').disabled, false);
      await element('#resolveBtn').click(); assert.equal(starts, 2);
    }
    if (name === 'live_wrong_mode') {
      assert.match(element('#runStatus').textContent, /failed/i);
      assert.equal(element('#downloadBtn').disabled, true);
      assert.doesNotMatch(element('#ruling').innerHTML, /Partial Refund/);
      return;
    }
    assert.equal(element('#resolveBtn').textContent, 'Run live API');
    assert.match(element('#runStatus').textContent, /live API.*completed/i);
    assert.doesNotMatch(element('#pipeline').innerHTML, /simulated responses/);
    assert.match(element('#pipeline').innerHTML, /live API/i);
    if (name === 'live_fallback' || name === 'live_guard_rejected') {
      assert.match(element('#runStatus').textContent, /fallback|rejected/i);
      assert.match(element('#runStatus').className, /warn/);
    } else if (name === 'live_unknown_agents') {
      assert.match(element('#runStatus').textContent, /status unavailable/i);
      assert.match(element('#runStatus').className, /warn/);
    }
    await element('#downloadBtn').click();
    const audit = JSON.parse(await downloads[0].text());
    assert.equal(audit.execution.mode, 'live');
    assert.match(audit.artifact, /live API/i); assert.doesNotMatch(audit.artifact, /simulation/);
    assert.equal(audit.payment_executed, false);
    assert.equal(createdElements.at(-1).download, 'ryde-live-test.json');
    run("showReference('evidence', 'e1')");
    assert.match(element('#referenceContent').innerHTML, /sample/i);
  }
}

async function simulationTest(name) {
  const ok = data => ({ok: true, json: async () => data});
  const event = {run_id: 'one', seq: 1, actor: 'Evidence Collection', kind: 'tool', status: 'started', input_summary: 'Read GPS', output_summary: '', evidence_ids: [], mode: 'simulation'};
  const complete = {run_id: 'one', status: 'completed', events: [], next_seq: 1, result: rulingResponse({run_id: 'one', execution: {mode: 'simulation', scenario: 'success'}})};
  if (name === 'simulation_metadata') {
    renderResponse(rulingResponse({agent_results: {rider: agentResult({is_simulated: true}), driver: agentResult({is_simulated: true, mode: 'fallback', status: 'rejected'})}}));
    assert.match(agentRow('rider'), /Simulated/);
    assert.doesNotMatch(agentRow('rider'), /LLM/);
    assert.match(agentRow('driver'), /Simulated.*Deterministic fallback/);
    assert.match(element('#ruling').innerHTML, /rule.*score/i);
    assert.match(element('#ruling').innerHTML, /not.*probability/i);
  } else if (name === 'simulation_poll') {
    setCase({}); element('#scenarioSelect').value = 'retry_success'; let polls = 0;
    context.fetch = async (url, options) => {
      if (url === '/api/runs') {assert.deepEqual(JSON.parse(options.body), {case_id: 'test', scenario: 'retry_success'}); return ok({run_id: 'one', status: 'running'});}
      if (url.startsWith('/api/runs/one?')) {
        if (++polls === 1) {assert.equal(url, '/api/runs/one?after=0'); return ok({run_id: 'one', status: 'running', events: [event], next_seq: 1, result: null});}
        assert.equal(url, '/api/runs/one?after=1'); assert.match(element('#pipeline').innerHTML, /Read GPS/);
        assert.doesNotMatch(element('#ruling').innerHTML, /Partial Refund/); return ok(complete);
      }
      if (url === '/api/health') return ok({state: 'no_key'});
      throw new Error('Unexpected ' + url);
    };
    await element('#resolveBtn').click(); assert.equal(polls, 2);
    assert.match(element('#ruling').innerHTML, /Partial Refund/);
    assert.equal(element('#downloadBtn').disabled, false);
    assert.match(element('#runStatus').textContent, /completed/i);
    await element('#downloadBtn').click();
    const audit = JSON.parse(await downloads[0].text());
    assert.equal(audit.payment_executed, false);
    assert.equal(audit.execution.mode, 'simulation');
    assert.equal(audit.result.run_id, 'one');
    assert.equal(audit.events[0].input_summary, 'Read GPS');
  } else if (name === 'simulation_failure_retry') {
    setCase({}); let attempt = 0;
    context.fetch = async url => {
      if (url === '/api/runs') {attempt++; return ok({run_id: 'one', status: 'running'});}
      if (url.startsWith('/api/runs/one?')) return ok(attempt === 1 ? {run_id: 'one', status: 'failed', next_seq: 0, events: [], error_code: 'run_failed', result: null} : complete);
      return ok({state: 'no_key'});
    };
    await element('#resolveBtn').click(); assert.match(element('#runStatus').textContent, /failed.*retry/i);
    assert.equal(element('#resolveBtn').disabled, false); assert.equal(element('#downloadBtn').disabled, true);
    await element('#resolveBtn').click(); assert.match(element('#ruling').innerHTML, /Partial Refund/);
  } else if (['simulation_stale_run', 'simulation_stale_post'].includes(name)) {
    setCase({}); let release; const pending = new Promise(resolve => {release = resolve;});
    context.fetch = async url => {
      if (url === '/api/runs') return name === 'simulation_stale_post' ? pending : ok({run_id: 'one', status: 'running'});
      if (url.startsWith('/api/runs/one?')) return pending;
      if (url === '/api/disputes/new') return ok({case_id: 'new', trip: {pickup: {name: 'New pickup'}}});
      if (url === '/api/health') return ok({state: 'no_key'});
      throw new Error('Unexpected ' + url);
    };
    const old = element('#resolveBtn').click(); await new Promise(resolve => setImmediate(resolve));
    await run("selectDispute('new')"); element('#resolveBtn').disabled = true;
    release(ok(name === 'simulation_stale_post' ? {run_id: 'one', status: 'running'} : complete)); await old;
    assert.equal(run('selected'), 'new'); assert.doesNotMatch(element('#ruling').innerHTML, /Partial Refund/);
    assert.equal(element('#resolveBtn').disabled, true, 'stale finally must not re-enable another run');
    assert.equal(element('#downloadBtn').disabled, true);
  } else if (name === 'simulation_rerun') {
    setCase({}); let release, starts = 0;
    const pending = new Promise(resolve => {release = resolve;});
    context.fetch = async url => {
      if (url === '/api/runs') return ok({run_id: ++starts === 1 ? 'old' : 'one', status: 'running'});
      if (url.startsWith('/api/runs/old?')) return pending;
      if (url.startsWith('/api/runs/one?')) return ok(complete);
      return ok({state: 'no_key'});
    };
    const old = element('#resolveBtn').click(); await new Promise(resolve => setImmediate(resolve));
    await element('#resolveBtn').click();
    release(ok({run_id:'old',status:'failed',error_code:'old_failed',events:[],next_seq:0})); await old;
    assert.match(element('#ruling').innerHTML, /Partial Refund/);
    assert.match(element('#runStatus').textContent, /completed/i);
    assert.equal(element('#downloadBtn').disabled, false);
    assert.equal(element('#resolveBtn').disabled, false);
  } else if (name === 'simulation_case_failure') {
    context.fetch = async () => ({ok:false,status:503,json:async () => ({detail:'Unavailable'})});
    await run("selectDispute('missing')");
    assert.equal(run('selectedData'), null);
    assert.equal(element('#resolveBtn').disabled, true);
    assert.match(element('#runStatus').textContent, /retry/);
    await element('#downloadBtn').click(); assert.equal(downloads.length, 0);
  } else if (name === 'simulation_event_escape') {
    context.eventFixture = [{seq:1,actor:'<img>',kind:'<script>',status:'completed',input_summary:'',output_summary:'<svg onload=x>',evidence_ids:[],mode:'simulation',duration_ms:null}];
    run('runEvents = eventFixture; renderRunEvents()');
    assert.doesNotMatch(element('#pipeline').innerHTML, /<img|<script|<svg/);
    assert.match(element('#pipeline').innerHTML, /&lt;svg/);
    assert.doesNotMatch(element('#pipeline').innerHTML, /In progress/);
  } else if (name === 'simulation_stale_case') {
    let release; const pending = new Promise(resolve => {release = resolve;});
    context.fetch = async url => url.endsWith('/old') ? pending : ok({case_id: 'new', trip: {pickup: {name: 'New pickup'}}});
    const old = run("selectDispute('old')"); await run("selectDispute('new')");
    release(ok({case_id: 'old'})); await old;
    assert.equal(run('selectedData.case_id'), 'new'); assert.match(panel(), /New pickup/);
  } else if (name === 'simulation_references') {
    const claim = {text: '<img src=x> supported claim', evidence_ids: ['e1'], policy_ids: ['p1']};
    const response = rulingResponse({rider_case: {structured: {claims: [claim]}}, driver_case: {structured: {claims: [claim]}},
      evidence_catalog: [{id: 'e1', value: 0, text: '<script>source</script>', source: 'sample', source_path: 'fare.total', version: 'v1'}],
      policy_catalog: [{id: 'p1', title: 'Refund policy', text: '<b>Policy text</b>', source: 'demo', source_path: 'policies[0]', version: 'pv1'}]});
    response.ruling.agent_output = {claims: [claim]}; renderResponse(response);
    const claims = element('#claims').innerHTML;
    for (const label of ['Rider Advocate', 'Driver Advocate', 'Judge']) assert.ok(claims.includes(label));
    assert.match(claims, /data-ref-id="e1"/); assert.match(claims, /data-ref-id="p1"/); assert.doesNotMatch(claims, /<img/);
    element('#resolveBtn').focus(); run("showReference('evidence', 'e1')");
    assert.match(element('#referenceContent').innerHTML, /fare.total/); assert.match(element('#referenceContent').innerHTML, /&lt;script&gt;/);
    assert.match(element('#referenceContent').innerHTML, /v1/); assert.match(element('#referenceContent').innerHTML, />0</);
    assert.equal(document.activeElement, element('#referenceClose'));
    document.listeners.keydown({key: 'Escape', preventDefault() {}}); assert.equal(document.activeElement, element('#resolveBtn'));
    run("showReference('policy', 'p1')"); assert.match(element('#referenceContent').innerHTML, /&lt;b&gt;Policy text/);
    assert.match(element('#referenceContent').innerHTML, /pv1/);
    run("showReference('evidence', '<missing>')"); assert.match(element('#referenceContent').innerHTML, /not found/i);
    assert.doesNotMatch(element('#referenceContent').innerHTML, /<missing>/);
  } else throw new Error('Unknown simulation test ' + name);
}

async function main() {
  if (scenario.startsWith('live_')) {
    await liveTest(scenario);
  } else if (scenario.startsWith('simulation_')) {
    await simulationTest(scenario);
  } else if (scenario === 'official_tabs') {
    setCase(input);
    for (const tab of ['gps', 'chat', 'fare', 'history']) {
      run(`renderEvidenceTab('${tab}')`);
      assert.match(panel(), /evt active/);
      assert.doesNotMatch(panel(), /undefined|NaN/);
    }
    run("renderEvidenceTab('fare')");
    assert.equal(rowValue(panel(), 'Distance fare (actual)'), 'Not provided');
    assert.equal(rowValue(panel(), 'Cancellation fee'), '5.00');
  } else if (scenario === 'fare_missing_and_zero') {
    setCase({ fare: {base_fare: null, distance_fare_actual: 0, total_charged: null,
      cancellation_fee: 0, currency: 'SGD'} });
    run("renderEvidenceTab('fare')");
    assert.equal(rowValue(panel(), 'Base fare'), 'Not provided');
    assert.equal(rowValue(panel(), 'Distance fare (actual)'), '0.00');
    assert.equal(rowValue(panel(), 'Distance fare (optimal)'), 'Not provided');
    assert.equal(rowValue(panel(), 'Total charged'), 'Not provided');
    assert.equal(rowValue(panel(), 'Cancellation fee'), '0.00');
  } else if (scenario === 'gps_missing_fields') {
    setCase({ trip: {} });
    run("renderEvidenceTab('gps')");
    for (const label of ['Pickup', 'Dropoff', 'Distance', 'Duration', 'Traffic detected'])
      assert.equal(rowValue(panel(), label), 'Not provided');
    assert.match(panel(), /GPS route: Not provided/);
    assert.doesNotMatch(panel(), /undefined|NaN/);
  } else if (scenario === 'gps_route_without_endpoints') {
    setCase({ trip: {}, gps: { actual_route: [[1.30, 103.8], [1.31, 103.81]] } });
    run("renderEvidenceTab('gps')");
    assert.match(panel(), /<svg/);
    assert.doesNotMatch(panel(), /NaN|undefined/);
  } else if (scenario === 'escape_numeric_and_null') {
    assert.equal(run('esc(0)'), '0');
    assert.equal(run('esc(12)'), '12');
    assert.equal(run('esc(null)'), '');
    assert.equal(run('esc(undefined)'), '');
  } else if (scenario === 'escape_evidence') {
    setCase({ fare: {currency: '<img src=x onerror=alert(1)>', total_charged: 0} });
    run("renderEvidenceTab('fare')");
    assert.doesNotMatch(panel(), /<img/);
    assert.match(panel(), /&lt;img/);
    setCase({trip: {actual_distance_km: '<img src=x>', pickup: {name: '<img src=x>'}}});
    run("renderEvidenceTab('gps')");
    assert.doesNotMatch(panel(), /<img/);
  } else if (scenario === 'resolve_clear_agent_result') {
    setCase({});
    renderResponse(rulingResponse({agent_results: {rider: agentResult(), driver: agentResult(), judge: agentResult()}}));
    assert.match(agentRow('rider'), /LLM/);
    context.fetch = async url => {
      if (url === '/api/runs') {
        assert.doesNotMatch(element('#agentResults').innerHTML, /test-model/);
        return {ok: false, status: 503, json: async () => ({detail: 'unavailable'})};
      }
      return {ok: true, json: async () => ({state: 'ok', model: 'global-model'})};
    };
    await element('#resolveBtn').listeners.click();
    assert.doesNotMatch(element('#agentResults').innerHTML, /test-model|global-model/);
    assert.match(element('#agentResults').innerHTML, /unavailable/i);
  } else if (scenario.startsWith('agents_')) {
    run('renderHealth({state: "ok", model: "global-model"})');
    const response = rulingResponse();
    if (scenario === 'agents_unknown_legacy') {
      delete response.ruling.reasoning_source;
      delete response.ruling.guard;
      renderResponse(response);
      for (const party of ['rider', 'driver', 'judge']) {
        assert.match(agentRow(party), /unavailable/i);
        assert.doesNotMatch(agentRow(party), /LLM|global-model/);
      }
      assert.doesNotMatch(element('#ruling').innerHTML, /Verified template|checks passed/i);
      assert.match(element('#ruling').innerHTML, /Partial Refund/);
    } else if (scenario === 'agents_mixed_modes') {
      response.agent_results = {rider: agentResult(), driver: agentResult({mode: 'fallback', status: 'error',
        error_code: 'timeout', attempts: 1}), judge: agentResult({model: 'judge-model', attempts: 2})};
      renderResponse(response);
      assert.match(agentRow('rider'), /LLM/);
      assert.match(agentRow('rider'), /test-model/);
      assert.match(agentRow('driver'), /Deterministic fallback/);
      assert.match(agentRow('driver'), /timeout/);
      assert.match(agentRow('judge'), /LLM/);
      assert.match(agentRow('judge'), /judge-model/);
      assert.match(agentRow('judge'), /Attempts: 2/);
      assert.match(agentRow('rider'), /advocate.v1/);
      assert.doesNotMatch(element('#agentResults').innerHTML, /global-model/);
    } else if (scenario === 'agents_fallback_reasons') {
      response.agent_results = {rider: agentResult({mode: 'fallback', status: 'no_key', model: null, attempts: 0}),
        driver: agentResult({mode: 'fallback', status: 'rejected', attempts: 2, error_code: 'invalid_reference',
          attempt_errors: ['invalid_json', 'invalid_reference']}), judge: {mode: 'llm'}};
      renderResponse(response);
      assert.match(agentRow('rider'), /no API key/);
      assert.match(agentRow('rider'), /Attempts: 0/);
      assert.match(agentRow('driver'), /draft rejected/i);
      assert.match(agentRow('driver'), /invalid_json/);
      assert.match(agentRow('driver'), /invalid_reference/);
      assert.match(agentRow('judge'), /unavailable/i);
      assert.doesNotMatch(agentRow('judge'), /LLM/);
    } else if (scenario === 'agents_escape_metadata') {
      const attack = '<img src=x onerror="alert(1)">';
      response.agent_results = {rider: agentResult({model: attack, prompt_version: attack,
        error_code: attack, attempt_errors: [attack]})};
      renderResponse(response);
      assert.match(agentRow('rider'), /&lt;img/);
      assert.doesNotMatch(element('#agentResults').innerHTML, /<img|<script/);
    }
  } else if (scenario.startsWith('guard_')) {
    const response = rulingResponse();
    if (scenario === 'guard_rejected') {
      response.ruling.guard.status = 'rejected';
      response.ruling.guard.reasons = ['invalid_action'];
    } else if (scenario === 'guard_escape') {
      response.ruling.guard.status = 'rejected';
      response.ruling.guard.reasons = ['<img src=x>'];
      response.ruling.guard.policy_version = '<svg onload=alert(1)>';
      response.ruling.currency = '<img src=currency>';
    }
    renderResponse(response);
    const markup = element('#ruling').innerHTML;
    assert.match(markup, /Verified template/);
    assert.match(markup, /checked evidence selection/);
    if (scenario === 'guard_approved') {
      assert.match(markup, /Reference checks passed/);
      assert.match(markup, /policy.v1/);
      assert.match(markup, /Checked references: 2/);
    } else if (scenario === 'guard_rejected') {
      assert.match(markup, /Model draft discarded/);
      assert.match(markup, /deterministic ruling applies/);
      assert.match(markup, /invalid_action/);
      assert.match(markup, /SGD 7.87/);
    } else {
      assert.doesNotMatch(markup, /<img|<svg onload/);
      assert.match(markup, /&lt;img/);
      assert.match(markup, /&lt;svg/);
    }
  } else if (scenario === 'trace_agent_result') {
    context.traceFixture = [{agent: 'Judge', role: 'decision', content: 'Done',
      meta: {llm: agentResult({mode: 'fallback', status: 'rejected', error_code: '<invalid>'})}}];
    run('animateTrace(traceFixture, () => {})');
    const markup = element('#pipeline').children[0].innerHTML;
    assert.match(markup, /Deterministic fallback/);
    assert.match(markup, /draft rejected/i);
    assert.match(markup, /&lt;invalid&gt;/);
    assert.doesNotMatch(markup, /<invalid>/);
  } else if (scenario.startsWith('resolve_')) {
    setCase({});
    const states = { state: 'fallback', model: 'test-model', llm_configured: true,
      last_call_ok: false, last_error: 'unavailable', success_count: 0, fail_count: 1 };
    const success = {trace: [{agent: 'Judge', role: 'decision', content: 'Done'}], duration_ms: 4,
      ruling: {action: 'no_action', amount: 0, currency: 'SGD', confidence: .8,
        reasoning: 'Evidence checked', escalated: false}};
    const response = scenario === 'resolve_http_error'
      ? {ok: false, status: 404, json: async () => ({detail: '<unknown case>'})}
      : scenario === 'resolve_validation_error'
      ? {ok: false, status: 422, json: async () => ({detail: [{loc: ['body', 'fare'], msg: 'Invalid amount'}]})}
      : scenario === 'resolve_plain_http_error'
      ? {ok: false, status: 503, json: async () => { throw new SyntaxError('not JSON'); }}
      : {ok: true, status: 200, json: async () => success};
    context.fetch = async url => {
      if (url === '/api/runs') return response.ok ? {ok: true, json: async () => ({run_id: 'legacy', status: 'running'})} : response;
      if (url.startsWith('/api/runs/legacy?')) return {ok: true, json: async () => ({run_id: 'legacy', status: 'completed', events: [], next_seq: 0, result: success, error_code: null})};
      if (url === '/api/health') {
        if (scenario === 'resolve_health_unavailable') throw new Error('health offline');
        return {ok: true, json: async () => states};
      }
      throw new Error(`Unexpected URL ${url}`);
    };
    run('renderHealth({state: "configured", model: "test-model"})');
    await element('#resolveBtn').listeners.click();
    assert.equal(element('#resolveBtn').disabled, false);
    assert.equal(element('#resolveBtn').textContent, 'Run simulation');
    if (scenario === 'resolve_http_error') {
      assert.match(element('#pipeline').innerHTML, /&lt;unknown case&gt;/);
      assert.doesNotMatch(element('#pipeline').innerHTML, /<unknown case>/);
      assert.match(element('#ruling').innerHTML, /could not be resolved/i);
    } else if (scenario === 'resolve_validation_error') {
      assert.match(element('#pipeline').innerHTML, /Invalid amount/);
    } else if (scenario === 'resolve_plain_http_error') {
      assert.match(element('#pipeline').innerHTML, /503/);
      assert.doesNotMatch(element('#pipeline').innerHTML, /not JSON/);
    } else {
      assert.match(element('#ruling').innerHTML, /No Action/);
      if (scenario === 'resolve_health_unavailable') {
        assert.match(element('#llmText').textContent, /status unavailable/i);
        assert.equal(element('#llmBadge .dot').className, 'dot off');
      } else {
        assert.match(element('#llmText').textContent, /falling back/);
        assert.equal(element('#llmBadge .dot').className, 'dot warn');
      }
    }
  } else if (scenario === 'architecture_states') {
    assert.match(run('architectureSvg({state: "ok", model: "<model>"})'), /LLM online.*&lt;model&gt;/);
    assert.match(run('architectureSvg({state: "configured", model: "m"})'), /not yet called/);
    assert.match(run('architectureSvg({state: "fallback", model: "m"})'), /last call failed/);
    assert.match(run('architectureSvg({state: "no_key"})'), /no API key/);
    assert.match(run('architectureSvg(null)'), /Status unavailable/);
  } else if (scenario === 'trace_replay') {
    run('animateTrace([{agent: "Judge", role: "decision", content: "Done"}], () => {})');
    assert.match(element('#pipeline').innerHTML, /Run replay/);
    assert.doesNotMatch(element('#pipeline').innerHTML, /live/i);
    assert.equal(element('#pipeline').children.length, 1);
    assert.match(element('#pipeline').children[0].innerHTML, /Done/);
  } else throw new Error(`Unknown scenario: ${scenario}`);
  console.log(`PASS ${scenario}`);
}

main().catch(error => { console.error(error); process.exitCode = 1; });
