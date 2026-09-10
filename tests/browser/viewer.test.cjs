const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const code = fs.readFileSync('watchport/static/app.js', 'utf8');

async function harness(handler = null) {
  const nodes = new Map();
  const events = new Map();
  const calls = [];
  const timers = new Map();
  let timerId = 0;
  const document = {hidden: false, getElementById(id) {
    if (!nodes.has(id)) nodes.set(id, {textContent: '', hidden: false, src: 'about:blank', value: ''});
    return nodes.get(id);
  }, addEventListener: (event, callback) => events.set(event, callback)};
  const context = vm.createContext({document, navigator: {onLine: true},
    window: {addEventListener: (event, callback) => events.set(event, callback)},
    location: {reload() {}}, console,
    setInterval: () => 1, setTimeout: (f) => {timers.set(++timerId, f); return timerId;}, clearTimeout: (id) => timers.delete(id),
    fetch: async (path, options) => {
      calls.push({path, options});
      if (handler) { const result = await handler(path, options); if (result) return result; }
      const data = path === '/api/status' ? {enrolled: true, authenticated: true, csrf: 'test-csrf', state: 'authenticated', indicatorHealthy: true, streamConfigured: true, adapterHealthy: true, viewers: 0} :
        path === '/api/view/start' ? {viewerUrl: 'https://desktop.example.ts.net/p/test', admissionMs: 120} : {ok: true};
      return {ok: true, json: async () => data};
    }});
  vm.runInContext(code, context);
  await new Promise(resolve => setImmediate(resolve));
  return {context, nodes, document, events, calls, timers, run: (text) => vm.runInContext(text, context)};
}

test('backgrounded phone never displays a late admission response', async () => {
  let finish;
  const h = await harness(path => path === '/api/view/start' ? new Promise(resolve => {finish = resolve;}) : null);
  const pending = h.run('start()');
  await new Promise(resolve => setImmediate(resolve));
  h.document.hidden = true;
  h.events.get('visibilitychange')();
  finish({ok: true, json: async () => ({viewerUrl: 'https://desktop.example.ts.net/p/late', admissionMs: 10})});
  await pending;
  assert.equal(h.nodes.get('stream').src, 'about:blank');
  assert.ok(h.calls.filter(x => x.path === '/api/view/stop').length >= 2);
});

test('foregrounding requires deliberate reopening after background', async () => {
  const h = await harness();
  await h.run('start()');
  assert.equal(h.nodes.get('live').textContent, 'VIEW OPEN');
  h.document.hidden = true;
  h.events.get('visibilitychange')();
  h.document.hidden = false;
  h.events.get('visibilitychange')();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.filter(x => x.path === '/api/view/start').length, 1);
  assert.equal(h.nodes.get('stream').src, 'about:blank');
});

test('authorization failure never schedules automatic reconnect', async () => {
  const h = await harness(path => path === '/api/view/heartbeat' ? {ok: false, status: 401, json: async () => ({detail: 'expired'})} : null);
  await h.run('start()');
  await h.run('heartbeat()');
  assert.equal(h.nodes.get('stream').src, 'about:blank');
  assert.equal(h.timers.size, 0);
  assert.equal(h.nodes.get('live').textContent, 'CLOSED');
});

test('manual reconnect cannot create authority when revocation is unconfirmed', async () => {
  const h = await harness(path => path === '/api/view/stop' ? {ok: false, status: 503, json: async () => ({detail: 'unconfirmed'})} : null);
  await h.run('start()');
  await h.nodes.get('reconnectButton').onclick();
  assert.equal(h.calls.filter(x => x.path === '/api/view/start').length, 1);
});

test('network retry first revokes old authority before starting a new view', async () => {
  let fail = true;
  const h = await harness(path => {
    if (path === '/api/view/heartbeat' && fail) {fail = false; throw new TypeError('offline');}
    return null;
  });
  await h.run('start()');
  await h.run('heartbeat()');
  assert.equal(h.timers.size, 1);
  await [...h.timers.values()][0]();
  const paths = h.calls.map(x => x.path);
  assert.deepEqual(paths.slice(-2), ['/api/view/stop', '/api/view/start']);
});
