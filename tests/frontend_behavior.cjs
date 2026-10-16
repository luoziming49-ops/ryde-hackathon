const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const scenario = process.argv[2];
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const html = fs.readFileSync('frontend/index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

class Element {
  constructor() {
    this.innerHTML = ''; this.textContent = ''; this.disabled = false;
    this.listeners = {}; this.children = []; this.className = ''; this.value = 'success'; this.hidden = false; this.dataset = {}; this.attributes = {};
    this.tagName = ''; this.lang = ''; this.isConnected = true; this.scrollTop = 0; this.scrollHeight = 999; this.open = false;
    this.classList = {
      contains: name => this.className.split(/\s+/).includes(name),
      add: name => { if (!this.classList.contains(name)) this.className = (this.className + ' ' + name).trim(); },
      remove: name => { this.className = this.className.split(/\s+/).filter(c => c !== name).join(' '); },
      toggle: (name, force) => { const enabled = force ?? !this.classList.contains(name); this.classList[enabled ? 'add' : 'remove'](name); return enabled; },
    };
  }
  focus() { document.activeElement = this; }
  setAttribute(key, value) { this.attributes[key] = String(value); if (key === 'lang') this.lang = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  removeAttribute(key) { delete this.attributes[key]; }
  click() { return this.listeners.click?.({target: this}); }
  addEventListener(type, handler) { this.listeners[type] = handler; }
  appendChild(child) { this.children.push(child); }
  querySelector() { return null; }
  querySelectorAll(selector) { return this === element('#disputeList') && selector === '.dispute' ? disputeCards() : []; }
}

const elements = new Map();
const element = selector => {
  if (!elements.has(selector)) elements.set(selector, new Element());
  return elements.get(selector);
};
const createdElements = [];
// Static translation targets are read from production markup; no dictionary is mocked.
const staticElements = [];
const decodeHtmlText = value => value.replace(/&(amp|quot|apos|lt|gt|#39|#(\d+)|#x([a-f0-9]+));/gi, (all, entity, decimal, hex) =>
  decimal ? String.fromCodePoint(Number(decimal)) : hex ? String.fromCodePoint(parseInt(hex, 16)) : ({amp: '&', quot: '"', apos: "'", lt: '<', gt: '>', '#39': "'"})[entity.toLowerCase()]);
for (const match of html.slice(0, html.indexOf('<script>')).matchAll(/<([a-z][\w-]*)([^<>]*)>/gi)) {
  const [, tag, attributes] = match;
  const attrs = Object.fromEntries([...attributes.matchAll(/([\w:-]+)="([^"]*)"/g)].map(m => [m[1], decodeHtmlText(m[2])]));
  if (!attrs.id && !Object.keys(attrs).some(key => key.startsWith('data-'))) continue;
  const el = attrs.id ? element('#' + attrs.id) : new Element();
  el.tagName = tag.toUpperCase(); el.id = attrs.id || ''; el.attributes = attrs;
  for (const [key, value] of Object.entries(attrs)) if (key.startsWith('data-')) el.dataset[key.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = value;
  if (attrs.class) el.className = attrs.class;
  const contentStart = match.index + match[0].length;
  el.textContent = decodeHtmlText(html.slice(contentStart, html.indexOf('</' + tag, contentStart)).replace(/<[^>]*>/g, '').trim());
  staticElements.push(el);
}
// Parse the production-rendered card buttons so clicks use their real listeners.
let cardsMarkup = null, renderedCards = [];
function disputeCards() {
  const markup = element('#disputeList').innerHTML;
  if (markup !== cardsMarkup) {
    renderedCards.forEach(card => {card.isConnected = false;});
    renderedCards = [];
    for (const [, rawAttributes, body] of markup.matchAll(/<button\b([^>]*)>([\s\S]*?)<\/button>/g)) {
      const attributes = Object.fromEntries([...rawAttributes.matchAll(/([\w:-]+)="([^"]*)"/g)].map(match => [match[1], decodeHtmlText(match[2])]));
      if (!attributes.class?.split(/\s+/).includes('dispute')) continue;
      const card = new Element(); card.tagName = 'BUTTON'; card.attributes = attributes;
      card.className = attributes.class; card.dataset.id = attributes['data-id']; card.innerHTML = body;
      const paragraph = new Element(); paragraph.tagName = 'P'; paragraph.innerHTML = body.match(/<p>([\s\S]*?)<\/p>/)?.[1] || '';
      paragraph.textContent = decodeHtmlText(paragraph.innerHTML.replace(/<[^>]*>/g, ''));
      card.querySelector = selector => selector === 'p' ? paragraph : null;
      renderedCards.push(card);
    }
    cardsMarkup = markup;
  }
  return renderedCards;
}
const staticQueryAll = selector => {
  if (selector === '.dispute') return disputeCards();
  if (selector === '#evtTabs button') return staticElements.filter(el => el.dataset.tab);
  const attribute = selector.match(/^\[([\w-]+)(?:="([^"]*)")?\]$/);
  if (attribute) return staticElements.filter(el => el.getAttribute(attribute[1]) != null && (attribute[2] === undefined || el.getAttribute(attribute[1]) === attribute[2]));
  return [];
};
// Model the real details node created by ruling.innerHTML, including its initial open attribute.
let reasonMarkup = null, reasonElement = null;
const queryDocument = selector => {
  if (selector !== '#originalReason') return element(selector);
  const markup = element('#ruling').innerHTML;
  const opening = markup.match(/<details\b[^>]*\bid="originalReason"[^>]*>/);
  if (!opening) { if (reasonElement) reasonElement.isConnected = false; reasonMarkup = null; reasonElement = null; return null; }
  if (markup !== reasonMarkup) {
    if (reasonElement) reasonElement.isConnected = false;
    reasonElement = new Element(); reasonElement.id = 'originalReason'; reasonElement.tagName = 'DETAILS';
    reasonElement.open = /\sopen(?:\s|=|>)/.test(opening[0]); reasonMarkup = markup;
  }
  return reasonElement;
};
const document = {
  querySelector: queryDocument, querySelectorAll: staticQueryAll, documentElement: new Element(),
  createElement: () => { const el = new Element(); createdElements.push(el); return el; }, activeElement: null, listeners: {},
  addEventListener(type, handler) { this.listeners[type] = handler; },
};
const downloads = [];
const urls = {createObjectURL(blob) { downloads.push(blob); return 'blob:local'; }, revokeObjectURL() {}};
const preferences = new Map();
const storageCalls = [];
const browserLanguage = ['i18n_browser_zh', 'i18n_saved_preference', 'i18n_invalid_storage', 'i18n_storage_read_error'].includes(scenario) ? 'zh-SG' : 'en-US';
if (scenario === 'i18n_saved_preference') preferences.set('ryde-language', 'en');
if (scenario === 'i18n_invalid_storage') preferences.set('ryde-language', 'not-a-language');
const localStorage = {
  getItem(key) { return preferences.get(key) ?? null; },
  setItem(key, value) { storageCalls.push([key, value]); if (scenario === 'i18n_storage_write_error') throw new Error('Storage write denied'); preferences.set(key, String(value)); },
};
const makePage = () => {
  const page = vm.createContext({ document, console, setTimeout: fn => fn(), clearTimeout: () => {}, AbortController, Blob, URL: urls,
    navigator: {language: browserLanguage}, localStorage, fetch: async () => { throw new Error('Unexpected network request'); }});
  if (scenario === 'i18n_storage_read_error') Object.defineProperty(page, 'localStorage', {get() {throw new Error('Storage access denied');}});
  // Avoid startup I/O; tests call production functions and actual event handlers.
  vm.runInContext(script.replace(/\ninit\(\);\s*$/, ''), page);
  return page;
};
const context = makePage();
const run = code => vm.runInContext(code, context);
const setCase = data => { context.fixture = data; run('selectedData = fixture; selected = "test";'); };
const panel = () => element('#evidencePanel').innerHTML;
const rowValue = (markup, label) => {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = markup.match(new RegExp(`<span class="k">${escaped}</span><span class="v">([^<]*)</span>`));
  assert.ok(match, `Missing row: ${label}`);
  return match[1];
};
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

async function languageTest(name) {
  assert.equal(run('typeof setLanguage'), 'function', 'The production page must expose its language switch');
  const switchLanguage = language => run(`setLanguage(${JSON.stringify(language)})`);
  const expectLanguage = language => {
    assert.equal(run('currentLanguage'), language);
    assert.equal(document.documentElement.lang, language === 'zh' ? 'zh-CN' : 'en');
    assert.equal(element('#languageSelect').value, language);
  };
  if (name === 'i18n_saved_preference') {
    expectLanguage('en'); // Saved English wins over zh-SG browser preference.
    switchLanguage('zh');
    expectLanguage('zh');
    assert.equal(preferences.get('ryde-language'), 'zh');
  } else if (name === 'i18n_selector_and_unknown') {
    assert.match(html, /<select[^>]*id="languageSelect"/);
    assert.equal(typeof element('#languageSelect').listeners.change, 'function');
    element('#languageSelect').value = 'zh';
    await element('#languageSelect').listeners.change({target: element('#languageSelect')});
    expectLanguage('zh');
    assert.match(element('#resolveBtn').textContent, /运行.*模拟|模拟.*运行/);
    const heading = staticElements.find(el => el.dataset.i18n === 'Dispute workbench');
    assert.ok(heading, 'Use the real workbench heading from production HTML');
    assert.match(heading.textContent, /争议/);
    assert.match(element('#languageSelect').getAttribute('aria-label'), /语言/);
    const writes = storageCalls.length;
    for (const invalid of ['fr', '', null, '<img>']) switchLanguage(invalid);
    expectLanguage('zh');
    assert.equal(storageCalls.length, writes, 'unknown languages must not overwrite preference');
    switchLanguage('en'); expectLanguage('en');
    assert.equal(element('#resolveBtn').textContent, 'Run simulation');
    assert.equal(heading.textContent, 'Dispute workbench');
  } else if (name === 'i18n_ruling_amounts') {
    const response = rulingResponse({evidence: {category: 'route_deviation', consent_report_state: 'unconfirmed'}});
    Object.assign(response.ruling, {action: 'insufficient_evidence', amount: null, confidence: null, escalated: true});
    renderResponse(response);
    const before = JSON.stringify(response);
    switchLanguage('zh');
    assert.match(element('#ruling').innerHTML, /证据不足/);
    assert.match(element('#ruling').innerHTML, /未.*派|尚未.*派/);
    assert.doesNotMatch(element('#ruling').innerHTML, /class="amount"|SGD 0\.00/);
    assert.equal(run('JSON.stringify(currentResult)'), before);
    switchLanguage('en');
    assert.match(element('#ruling').innerHTML, /Insufficient Evidence/);
    const zero = rulingResponse(); Object.assign(zero.ruling, {action: 'no_action', amount: 0});
    renderResponse(zero); switchLanguage('zh');
    assert.match(element('#ruling').innerHTML, /SGD 0\.00/);
    assert.equal(run('currentResult.ruling.amount'), 0);
    switchLanguage('en'); assert.match(element('#ruling').innerHTML, /No Action/);
  } else if (name === 'i18n_context_preserved') {
    context.fetch = async url => ({ok: true, json: async () => url === '/api/health' ? {state: 'no_key'} : []});
    await run('init()');
    setCase({category: 'route_deviation', fare: {currency: 'SGD', cancellation_fee: 0, total_charged: 0}, rider: {}, driver: {}});
    const fareTab = staticElements.find(el => el.dataset.tab === 'fare');
    assert.equal(typeof fareTab.listeners.click, 'function');
    await fareTab.click();
    assert.equal(fareTab.classList.contains('active'), true);
    element('#scenarioSelect').value = 'retry_success';
    const response = rulingResponse({evidence_catalog: [{id: 'e1', text: 'Original <source>', source: 'sample'}]});
    renderResponse(response); element('#downloadBtn').disabled = false;
    element('#resolveBtn').focus(); run("showReference('evidence', 'e1')");
    const before = run('JSON.stringify([selected, selectedData, selectedMode, currentResult, runEvents, requestGeneration])');
    let requests = 0; context.fetch = async () => {requests++; throw new Error('No request during language switch');};
    switchLanguage('zh');
    assert.equal(run('JSON.stringify([selected, selectedData, selectedMode, currentResult, runEvents, requestGeneration])'), before);
    assert.equal(element('#scenarioSelect').value, 'retry_success');
    assert.equal(fareTab.classList.contains('active'), true, 'The visible active tab must remain selected');
    assert.equal(element('#downloadBtn').disabled, false);
    assert.match(panel(), /SGD/); assert.doesNotMatch(panel(), /<svg/);
    assert.equal(run('openModalId'), 'referenceModal');
    assert.match(element('#referenceTitle').textContent, /e1/);
    assert.match(element('#referenceContent').innerHTML, /Original &lt;source&gt;/);
    assert.equal(requests, 0);
    switchLanguage('en');
    document.listeners.keydown({key: 'Escape', preventDefault() {}});
    assert.equal(document.activeElement, element('#resolveBtn'));
  } else if (['i18n_default_en', 'i18n_browser_zh', 'i18n_invalid_storage', 'i18n_storage_read_error', 'i18n_storage_write_error'].includes(name)) {
    expectLanguage(['i18n_browser_zh', 'i18n_invalid_storage', 'i18n_storage_read_error'].includes(name) ? 'zh' : 'en');
    switchLanguage('zh'); expectLanguage('zh');
    assert.match(element('#resolveBtn').textContent, /运行.*模拟|模拟.*运行/);
    switchLanguage('en'); expectLanguage('en');
    assert.equal(element('#resolveBtn').textContent, 'Run simulation');
  } else if (name === 'i18n_reload_preference') {
    switchLanguage('zh');
    assert.equal(preferences.get('ryde-language'), 'zh');
    const reloaded = makePage();
    assert.equal(vm.runInContext('currentLanguage', reloaded), 'zh');
    assert.equal(document.documentElement.lang, 'zh-CN');
    assert.equal(element('#languageSelect').value, 'zh');
  } else if (name === 'i18n_health_live_gate') {
    setCase({}); run('renderHealth({state: "configured", model: "model-original", live_enabled: true, live_model: "model-original"})');
    switchLanguage('zh');
    assert.match(element('#llmText').textContent, /已配置/);
    assert.match(element('#llmText').textContent, /model-original/);
    assert.equal(element('#liveModeOption').disabled, false);
    assert.equal(run('selectedMode'), 'simulation');
    element('#modeSelect').value = 'live'; await element('#modeSelect').listeners.change({target: element('#modeSelect')});
    assert.equal(element('#scenarioControl').hidden, true);
    assert.match(element('#modeDescription').textContent, /费用|计费/);
    run('renderHealth(null)');
    assert.equal(element('#resolveBtn').disabled, true);
    switchLanguage('en');
    assert.equal(run('selectedMode'), 'live');
    assert.equal(element('#liveModeOption').disabled, true);
    assert.equal(element('#resolveBtn').disabled, true);
    assert.match(element('#llmText').textContent, /unavailable/i);
    let requests = 0; context.fetch = async () => {requests++; throw new Error('Live must stay blocked');};
    await element('#resolveBtn').click(); assert.equal(requests, 0);
    switchLanguage('zh'); assert.equal(element('#resolveBtn').disabled, true);
  } else if (name === 'i18n_source_preservation') {
    const raw = 'No Action <script>original source</script>';
    setCase({category: 'route_deviation', rider: {claim: raw}, driver: {response: raw}, chat_log: [{from: 'rider', text: raw}]});
    run("renderEvidenceTab('gps')"); switchLanguage('zh');
    assert.match(panel(), /No Action &lt;script&gt;original source&lt;\/script&gt;/);
    assert.doesNotMatch(panel(), /<script>/);
    run("renderEvidenceTab('chat')"); switchLanguage('en'); switchLanguage('zh');
    assert.match(panel(), /No Action &lt;script&gt;original source&lt;\/script&gt;/);
    const response = rulingResponse({rider_case: {structured: {claims: [{text: raw, evidence_ids: ['e1'], policy_ids: []}]}},
      evidence_catalog: [{id: 'e1', text: raw, value: '<img src=original>', source: 'sample'}]});
    response.ruling.reasoning = raw;
    renderResponse(response); const before = JSON.stringify(response);
    switchLanguage('en'); switchLanguage('zh');
    assert.equal(run('JSON.stringify(currentResult)'), before);
    assert.match(element('#claims').innerHTML, /No Action &lt;script&gt;original source&lt;\/script&gt;/);
    assert.match(element('#ruling').innerHTML, /No Action &lt;script&gt;original source&lt;\/script&gt;/);
    run("showReference('evidence', 'e1')");
    assert.match(element('#referenceContent').innerHTML, /No Action &lt;script&gt;original source&lt;\/script&gt;/);
    assert.match(element('#referenceContent').innerHTML, /&lt;img src=original&gt;/);
    assert.doesNotMatch(element('#claims').innerHTML + element('#ruling').innerHTML + element('#referenceContent').innerHTML, /<script>|<img/);
  } else if (name === 'i18n_review_questions') {
    const response = rulingResponse();
    Object.assign(response.ruling, {action: 'insufficient_evidence', amount: null, confidence: null, escalated: true,
      review_questions: ["Did the rider agree to the route change, including any oral discussion? Record each party's account separately and resolve missing or conflicting reports.",
        'Was the additional stop explained and agreed to, and did it change the fare? Route agreement alone does not answer this.',
        'What traffic or safety reason supports the detour? No traffic finding was supplied.',
        'Does the supplied traffic explanation account for the extent of this detour?',
        'Unmapped question <img src=original>', 'No Action']});
    renderResponse(response); switchLanguage('zh');
    const markup = element('#ruling').innerHTML;
    assert.match(markup, /待核实|需要核实/);
    assert.match(markup, /口头/); assert.match(markup, /停靠|停留/); assert.match(markup, /路况|交通/);
    assert.match(markup, /Unmapped question &lt;img src=original&gt;/);
    assert.match(markup, /No Action/, 'An unknown question must stay original even if it matches another UI dictionary key');
    assert.doesNotMatch(markup, /<img/);
    assert.deepEqual(JSON.parse(run('JSON.stringify(currentResult.ruling.review_questions)')), response.ruling.review_questions);
    switchLanguage('en'); assert.match(element('#ruling').innerHTML, /Did the rider agree to the route change/);
  } else if (name === 'i18n_api_response') {
    assert.ok(input && input.ruling, 'Use the actual offline API response supplied by pytest');
    renderResponse(input); const before = JSON.stringify(input);
    switchLanguage('zh');
    const markup = element('#ruling').innerHTML;
    assert.match(markup, input.ruling.action === 'insufficient_evidence' ? /证据不足/ : /部分退款/);
    if (input.ruling.amount === null) {
      assert.doesNotMatch(markup, /class="amount"|SGD 0\.00/);
      assert.match(markup, /口头/);
    } else assert.match(markup, /SGD 7\.87/);
    context.originalReasoning = input.ruling.reasoning;
    assert.ok(markup.includes(run('esc(originalReasoning)')), 'Original API reasoning remains inspectable');
    assert.equal(run('JSON.stringify(currentResult)'), before);
    switchLanguage('en'); assert.equal(run('JSON.stringify(currentResult)'), before);
  } else if (['i18n_running_no_side_effects', 'i18n_live_running_no_side_effects', 'i18n_completed_status', 'i18n_error_status'].includes(name)) {
    const ok = data => ({ok: true, json: async () => data});
    const live = name === 'i18n_live_running_no_side_effects';
    setCase({case_id: 'test', category: 'route_deviation', fare: {currency: 'SGD', cancellation_fee: 0, total_charged: 0}});
    run('renderHealth({state: "configured", model: "model-original", live_enabled: true})');
    if (live) {element('#modeSelect').value = 'live'; await element('#modeSelect').listeners.change({target: element('#modeSelect')});}
    const mode = live ? 'live' : 'simulation';
    const response = rulingResponse({case_id: 'test', execution: {mode}, agent_results: {rider: agentResult(), driver: agentResult(), judge: agentResult()}});
    const event = {seq: 1, actor: 'Judge', kind: 'rule', status: 'completed', output_summary: 'Original <audit> text', mode};
    const complete = {run_id: 'language-run', status: 'completed', events: [event], next_seq: 1, result: response};
    let release; const pending = new Promise(resolve => {release = resolve;});
    const requests = [];
    context.fetch = async (url, options) => {
      requests.push({url, options});
      if (url === '/api/health') return ok({state: 'configured', model: 'model-original', live_enabled: true});
      if (url === (live ? '/api/live-runs' : '/api/runs')) {
        if (name === 'i18n_error_status') return {ok: false, status: 503, json: async () => ({detail: 'Original provider detail <danger>'})};
        return ok({run_id: 'language-run', status: 'running'});
      }
      if (url.startsWith('/api/runs/language-run?')) return name.endsWith('no_side_effects') ? pending : ok(complete);
      throw new Error('Unexpected ' + url);
    };
    element('#scenarioSelect').value = 'retry_success';
    const work = element('#resolveBtn').click();
    if (name.endsWith('no_side_effects')) {
      await new Promise(resolve => setImmediate(resolve));
      assert.equal(run('runInProgress'), true);
      const state = run('JSON.stringify([selected, selectedData, selectedMode, runEvents, currentResult, requestGeneration])');
      const signal = requests[0].options.signal; const count = requests.length;
      run("renderEvidenceTab('fare')"); element('#pipeline').scrollTop = 37;
      switchLanguage('zh');
      assert.equal(requests.length, count, 'Language change must not fetch, restart or poll');
      assert.equal(signal.aborted, false);
      assert.equal(run('activeController.signal'), signal);
      assert.equal(run('JSON.stringify([selected, selectedData, selectedMode, runEvents, currentResult, requestGeneration])'), state);
      assert.equal(run('runInProgress'), true);
      assert.equal(element('#resolveBtn').disabled, true);
      assert.match(element('#resolveBtn').textContent, /运行中|正在运行/);
      assert.equal(element('#scenarioSelect').value, 'retry_success');
      assert.equal(element('#pipeline').scrollTop, 37);
      assert.match(panel(), /SGD/);
      release(ok(complete));
    }
    await work;
    const count = requests.length; switchLanguage('zh');
    assert.equal(requests.length, count);
    if (name === 'i18n_error_status') {
      assert.match(element('#runStatus').textContent, /失败/);
      assert.match(element('#pipeline').innerHTML, /Original provider detail &lt;danger&gt;/);
      assert.doesNotMatch(element('#pipeline').innerHTML, /<danger>/);
      assert.equal(element('#downloadBtn').disabled, true);
      switchLanguage('en'); assert.match(element('#runStatus').textContent, /failed/i);
      assert.match(element('#pipeline').innerHTML, /Original provider detail &lt;danger&gt;/);
    } else {
      assert.match(element('#runStatus').textContent, /完成/);
      assert.doesNotMatch(element('#runStatus').textContent, /就绪|ready/i);
      assert.equal(element('#downloadBtn').disabled, false);
      assert.equal(run('currentResult.ruling.amount'), 7.87);
      assert.equal(requests.filter(r => r.options?.method === 'POST').length, 1);
      await element('#downloadBtn').click(); const zhAudit = JSON.parse(await downloads.at(-1).text());
      switchLanguage('en'); assert.match(element('#runStatus').textContent, /completed/i);
      await element('#downloadBtn').click(); const enAudit = JSON.parse(await downloads.at(-1).text());
      assert.deepEqual(enAudit, zhAudit, 'Language switch must not alter the exported audit');
      assert.deepEqual(enAudit.result, response); assert.deepEqual(enAudit.events, [event]);
    }
  } else if (name === 'i18n_loading_case') {
    let release; const pending = new Promise(resolve => {release = resolve;}); const requests = [];
    context.fetch = async (url, options) => {requests.push({url, options}); return pending;};
    const work = run("selectDispute('language-case')");
    const generation = run('requestGeneration'); const signal = requests[0].options.signal;
    switchLanguage('zh');
    assert.equal(requests.length, 1); assert.equal(signal.aborted, false);
    assert.equal(run('requestGeneration'), generation);
    assert.equal(run('selectedData'), null); assert.equal(element('#resolveBtn').disabled, true);
    assert.match(element('#runStatus').textContent, /加载|读取/);
    release({ok: true, json: async () => ({case_id: 'language-case', trip: {pickup: {name: 'Original pickup'}}})});
    await work;
    assert.match(element('#runStatus').textContent, /就绪/);
    assert.match(panel(), /Original pickup/);
    assert.equal(element('#resolveBtn').disabled, false);
  } else if (name === 'i18n_event_roles') {
    const roles = ['gather', 'evidence', 'argue', 'deliberate', 'rule', 'risk', 'retrieve'];
    const raw = roles.join(' ') + ' <original>';
    const events = roles.map((kind, i) => ({seq: i + 1, actor: 'Judge', kind, status: 'completed', mode: 'simulation', output_summary: raw}));
    context.languageEvents = events; run('runEvents = languageEvents; renderRunEvents()');
    switchLanguage('zh');
    const markup = element('#pipeline').innerHTML;
    const renderedRoles = [...markup.matchAll(/<div class="role">([\s\S]*?)<\/div>/g)].map(match => match[1]);
    assert.equal(renderedRoles.length, roles.length);
    for (const text of renderedRoles) assert.doesNotMatch(text, /\b(gather|evidence|argue|deliberate|rule|risk|retrieve)\b/, 'Known backend roles must be translated');
    assert.ok(markup.includes(raw.replace('<original>', '&lt;original&gt;')), 'Original event output remains unmodified');
    assert.equal(run('JSON.stringify(runEvents)'), JSON.stringify(events));
    switchLanguage('en');
    for (const role of roles) assert.match(element('#pipeline').innerHTML, new RegExp(' · ' + role + ' · '));
  } else if (name === 'i18n_duplicate_reference_focus') {
    const response = rulingResponse({evidence_catalog: [{id: 'same-id', text: 'Original shared reference', source: 'sample'}]});
    const makeTrigger = () => {const el = new Element(); el.dataset = {refKind: 'evidence', refId: 'same-id'}; return el;};
    let references = [makeTrigger(), makeTrigger()];
    document.querySelectorAll = selector => selector === '[data-ref-id]' ? references : staticQueryAll(selector);
    renderResponse(response);
    references[1].focus(); run("showReference('evidence', 'same-id')");
    // Without replacement, the exact connected trigger must win over the first duplicate.
    run('closeModal()'); assert.equal(document.activeElement, references[1]);
    references[1].focus(); run("showReference('evidence', 'same-id')");
    const old = references;
    switchLanguage('zh');
    // Browser boundary: innerHTML replacement detaches old buttons and creates their counterparts.
    old.forEach(el => {el.isConnected = false;}); references = [makeTrigger(), makeTrigger()];
    document.listeners.keydown({key: 'Escape', preventDefault() {}});
    assert.equal(document.activeElement, references[1], 'Return to the corresponding second reference after rerender, not the first duplicate');
  } else if (name === 'i18n_original_reason_disclosure') {
    renderResponse(rulingResponse());
    assert.equal(document.querySelector('#originalReason').open, true, 'English initially preserves the previously visible explanation');
    document.querySelector('#originalReason').open = false;
    switchLanguage('zh'); assert.equal(document.querySelector('#originalReason').open, false);
    document.querySelector('#originalReason').open = true;
    switchLanguage('en'); assert.equal(document.querySelector('#originalReason').open, true, 'Language change preserves the user disclosure choice');
    switchLanguage('zh');
    const response = rulingResponse(); response.ruling.reasoning = 'Another original explanation';
    renderResponse(response);
    assert.equal(document.querySelector('#originalReason').open, false, 'A newly rendered Chinese result initially shows its structured summary');
  } else if (name === 'i18n_startup_error_status') {
    let requests = 0;
    context.fetch = async () => {requests++; throw new Error('Backend unreachable test boundary');};
    await run('init()');
    assert.match(element('#llmText').textContent, /Backend unreachable/);
    const count = requests;
    switchLanguage('zh');
    assert.match(element('#llmText').textContent, /无法连接后端|后端.*不可达|后端.*无法/);
    assert.match(element('#disputeList').innerHTML, /无法加载|加载失败/);
    assert.equal(element('#liveModeOption').disabled, true);
    assert.equal(requests, count);
    switchLanguage('en');
    assert.match(element('#llmText').textContent, /Backend unreachable/);
    assert.match(element('#disputeList').innerHTML, /Could not load cases/);
  } else if (name === 'i18n_architecture_modal') {
    let requests = 0;
    context.fetch = async url => {requests++; assert.equal(url, '/api/health'); return {ok: true, json: async () => ({state: 'configured', model: 'model-original'})};};
    element('#archBtn').focus(); await element('#archBtn').click();
    assert.equal(requests, 1); assert.equal(run('openModalId'), 'archModal');
    switchLanguage('zh');
    assert.equal(requests, 1, 'Architecture language switch must use cached health');
    assert.equal(run('openModalId'), 'archModal');
    assert.match(element('#archTitle').textContent, /架构/);
    assert.match(element('#archSvg').innerHTML, /model-original/);
    switchLanguage('en');
    assert.equal(requests, 1); assert.match(element('#archTitle').textContent, /architecture/i);
    document.listeners.keydown({key: 'Escape', preventDefault() {}});
    assert.equal(document.activeElement, element('#archBtn'));
  } else throw new Error('Unknown language test ' + name);
}

async function fulltextTest(name) {
  const claim = 'Original long claim. '.repeat(25) + '\n保留这段完整陈述 <img src=original> END-OF-CLAIM';
  const listing = [{case_id: 'fulltext-one', category: 'route_deviation', rider_claim: claim},
    {case_id: 'fulltext-two', category: 'no_show', rider_claim: 'Second original claim'}];
  const loaded = id => ({case_id: id, category: id === 'fulltext-one' ? 'route_deviation' : 'no_show',
    rider: {claim: listing.find(row => row.case_id === id).rider_claim}, driver: {}, trip: {}});
  const ok = data => ({ok: true, json: async () => data});
  context.cardListing = listing; run('disputes = cardListing; renderDisputes()');
  let calls = [];
  context.fetch = async (url, options) => {calls.push({url, options}); return ok(loaded(url.split('/').at(-1)));};
  const card = id => disputeCards().find(node => node.dataset.id === id);
  const expectExpanded = id => {
    for (const node of disputeCards()) {
      assert.equal(node.classList.contains('active'), node.dataset.id === id);
      assert.equal(node.getAttribute('aria-expanded'), String(node.dataset.id === id));
      assert.equal(node.tagName, 'BUTTON'); assert.equal(node.getAttribute('type'), 'button');
    }
  };
  if (name === 'case_fulltext_selection') {
    expectExpanded(null);
    await card('fulltext-one').click(); expectExpanded('fulltext-one');
    assert.equal(run('selectedData.case_id'), 'fulltext-one');
    assert.equal(card('fulltext-one').querySelector('p').textContent, claim, 'The complete source text must remain in the selected card');
    assert.match(card('fulltext-one').innerHTML, /&lt;img src=original&gt; END-OF-CLAIM/);
    assert.doesNotMatch(card('fulltext-one').innerHTML, /<img/);
    await card('fulltext-two').click(); expectExpanded('fulltext-two');
    assert.equal(calls.length, 2);
  } else if (name === 'case_fulltext_language') {
    await card('fulltext-one').click();
    for (const language of ['zh', 'en']) {
      run(`setLanguage('${language}')`); expectExpanded('fulltext-one');
      assert.ok(card('fulltext-one').querySelector('p').textContent.endsWith(claim));
      assert.doesNotMatch(card('fulltext-one').innerHTML, /<img/);
      assert.equal(run('selected'), 'fulltext-one');
      assert.equal(run('JSON.stringify(disputes)'), JSON.stringify(listing));
    }
    assert.equal(calls.length, 1, 'Translating the expanded card must not reload it');
  } else if (name === 'case_fulltext_reselect_loaded') {
    await card('fulltext-one').click();
    renderResponse(rulingResponse()); element('#downloadBtn').disabled = false;
    const before = run('JSON.stringify([currentResult, runEvents, requestGeneration])');
    const controller = run('activeController'); const count = calls.length;
    await card('fulltext-one').click();
    assert.equal(calls.length, count, 'Reselecting the loaded card must not fetch');
    assert.equal(run('JSON.stringify([currentResult, runEvents, requestGeneration])'), before);
    assert.equal(run('activeController'), controller); assert.equal(controller.signal.aborted, false);
    assert.equal(element('#downloadBtn').disabled, false);
    // Exercise a real in-flight run, rather than setting the busy flag in the fixture.
    let release; const pending = new Promise(resolve => {release = resolve;});
    context.fetch = async (url, options) => {
      calls.push({url, options});
      if (url === '/api/runs') return pending;
      if (url.startsWith('/api/runs/card-run?')) return ok({run_id: 'card-run', status: 'completed', events: [], next_seq: 0,
        result: rulingResponse({execution: {mode: 'simulation'}})});
      if (url === '/api/health') return ok({state: 'no_key'});
      return ok(loaded(url.split('/').at(-1)));
    };
    const work = element('#resolveBtn').click();
    const runningController = run('activeController'); const generation = run('requestGeneration'); const runningCalls = calls.length;
    try {
      assert.equal(run('runInProgress'), true);
      await card('fulltext-one').click();
      assert.equal(calls.length, runningCalls); assert.equal(run('requestGeneration'), generation);
      assert.equal(run('activeController'), runningController); assert.equal(runningController.signal.aborted, false);
      assert.equal(run('runInProgress'), true);
    } finally {
      release(ok({run_id: 'card-run', status: 'running'})); await work;
    }
    assert.equal(run('currentResult.ruling.amount'), 7.87);
  } else if (name === 'case_fulltext_retry_failure') {
    let attempts = 0;
    context.fetch = async () => ++attempts === 1
      ? {ok: false, status: 503, json: async () => ({detail: 'Temporary case failure'})}
      : ok(loaded('fulltext-one'));
    await card('fulltext-one').click();
    assert.equal(run('selected'), 'fulltext-one'); assert.equal(run('selectedData'), null);
    assert.match(element('#runStatus').textContent, /retry/i);
    await card('fulltext-one').click();
    assert.equal(attempts, 2); assert.equal(run('selectedData.case_id'), 'fulltext-one');
    assert.equal(element('#resolveBtn').disabled, false);
  } else throw new Error('Unknown card test ' + name);
}

async function main() {
  if (scenario.startsWith('case_fulltext_')) {
    await fulltextTest(scenario);
  } else if (scenario.startsWith('i18n_')) {
    await languageTest(scenario);
  } else if (scenario.startsWith('live_')) {
    await liveTest(scenario);
  } else if (scenario.startsWith('simulation_')) {
    await simulationTest(scenario);
  } else if (scenario === 'consent_input_statements') {
    setCase({category: 'route_deviation', rider: {route_consent: 'agreed'}, driver: {route_consent: 'not_agreed'}});
    run("renderEvidenceTab('gps')");
    assert.match(panel(), /Route consent/i);
    assert.equal(rowValue(panel(), 'Rider statement'), 'Agreed');
    assert.equal(rowValue(panel(), 'Driver statement'), 'Did not agree');
    assert.match(panel(), /not independently verified/i);
    assert.doesNotMatch(panel(), /Statements consistent|consent verified/i);
  } else if (scenario === 'consent_missing_statements') {
    setCase({category: 'route_deviation', rider: {}, driver: {route_consent: '<img src=x>'}});
    run("renderEvidenceTab('gps')");
    assert.equal(rowValue(panel(), 'Rider statement'), 'Unknown');
    assert.equal(rowValue(panel(), 'Driver statement'), 'Unknown');
    assert.doesNotMatch(panel(), /<img|undefined|NaN/);
  } else if (scenario === 'consent_original_text') {
    setCase({category: 'route_deviation', rider: {claim: 'I agreed to the route <or did I?>'},
      driver: {response: 'Rider said "yes" <img src=x onerror="alert(1)">'}});
    run("renderEvidenceTab('gps')");
    assert.match(panel(), /I agreed to the route &lt;or did I\?&gt;/);
    assert.match(panel(), /Rider said &quot;yes&quot; &lt;img/);
    assert.equal(rowValue(panel(), 'Rider statement'), 'Unknown', 'free text must not infer structured consent');
    assert.equal(rowValue(panel(), 'Driver statement'), 'Unknown', 'free text must not infer structured consent');
    assert.doesNotMatch(panel(), /<img|<or did/);
  } else if (scenario.startsWith('consent_result_')) {
    const fixtures = {
      consent_result_consistent_agreed: ['agreed', 'agreed', 'consistent', 'agreed', 'Statements consistent', 'Agreed', 'Agreed'],
      consent_result_consistent_not_agreed: ['not_agreed', 'not_agreed', 'consistent', 'not_agreed', 'Statements consistent', 'Did not agree', 'Did not agree'],
      consent_result_conflicting: ['agreed', 'not_agreed', 'conflicting', null, 'Statements conflicting', 'Agreed', 'Did not agree'],
      consent_result_unconfirmed: ['unknown', 'agreed', 'unconfirmed', null, 'Statements unconfirmed', 'Unknown', 'Agreed'],
      consent_result_legacy: [undefined, undefined, undefined, undefined, 'Statements unconfirmed', 'Unknown', 'Unknown'],
    };
    const [rider, driver, state, consistent, label, riderLabel, driverLabel] = fixtures[scenario];
    setCase({category: 'route_deviation', rider: {route_consent: 'not_agreed'}, driver: {route_consent: 'not_agreed'}});
    const response = rulingResponse({evidence: {category: 'route_deviation', rider_route_consent: rider,
      driver_route_consent: driver, consent_report_state: state, consent_consistent_value: consistent}});
    renderResponse(response);
    const markup = element('#ruling').innerHTML;
    assert.match(markup, new RegExp(label));
    assert.equal(rowValue(markup, 'Rider statement'), riderLabel);
    assert.equal(rowValue(markup, 'Driver statement'), driverLabel);
    assert.match(markup, /not independently verified/i);
    assert.doesNotMatch(markup, /consent verified|agreement verified/i);
  } else if (scenario === 'review_questions_escape') {
    const response = rulingResponse({evidence: {category: 'route_deviation', rider_route_consent: '<img src=rider>',
      driver_route_consent: '<script>driver</script>', consent_report_state: '<svg onload=alert(1)>',
      consent_consistent_value: '<img src=consistent>'}});
    response.ruling.review_questions = ['Did the rider agree to <this route>?', '<img src=x onerror="alert(1)">'];
    renderResponse(response);
    const markup = element('#ruling').innerHTML;
    assert.match(markup, /Questions to verify/i);
    assert.match(markup, /Did the rider agree to &lt;this route&gt;\?/);
    assert.match(markup, /&lt;img src=x onerror=&quot;alert\(1\)&quot;&gt;/);
    assert.match(markup, /Statements unconfirmed/);
    assert.doesNotMatch(markup, /<img|<script|<svg onload/);
  } else if (scenario === 'review_questions_absent') {
    for (const value of [undefined, null, [], 'not an array']) {
      const response = rulingResponse();
      response.ruling.review_questions = value;
      renderResponse(response);
      assert.doesNotMatch(element('#ruling').innerHTML, /Questions to verify|undefined|NaN/);
      assert.match(element('#ruling').innerHTML, /Partial Refund/);
    }
  } else if (scenario === 'review_flag_no_dispatch') {
    const response = rulingResponse();
    Object.assign(response.ruling, {action: 'insufficient_evidence', amount: null, confidence: null, escalated: true,
      review_questions: ['Confirm the route consent with both parties.']});
    renderResponse(response);
    const markup = element('#ruling').innerHTML;
    assert.match(markup, /Flagged for human review/i);
    assert.match(markup, /no support case has been dispatched/i);
    assert.match(markup, /Confirm the route consent with both parties/);
    assert.doesNotMatch(markup, /SGD 0\.00|class="amount"|Escalated to human review/);
  } else if (scenario === 'consent_no_show') {
    setCase({category: 'no_show', rider: {route_consent: 'agreed'}, driver: {route_consent: 'agreed'}});
    run("renderEvidenceTab('gps')");
    assert.doesNotMatch(panel(), /Route consent|Rider statement|Driver statement/);
    renderResponse(rulingResponse({evidence: {category: 'no_show', consent_report_state: 'unconfirmed'}}));
    assert.doesNotMatch(element('#ruling').innerHTML, /Route consent|Statements unconfirmed/);
  } else if (scenario === 'gps_input_provenance') {
    setCase({category: 'route_deviation', trip: {actual_distance_km: 12, optimal_distance_km: 10, traffic_detected: true},
      gps: {actual_route: [[1.30, 103.8], [1.31, 103.81]]}});
    run("renderEvidenceTab('gps')");
    assert.match(panel(), /Route sketch from supplied coordinates/i);
    assert.match(panel(), /Distance and traffic are case-file inputs, not map-verified/i);
    assert.equal(rowValue(panel(), 'Distance'), '12 km (optimal 10 km)');
    assert.equal(rowValue(panel(), 'Traffic detected'), 'Yes');
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
