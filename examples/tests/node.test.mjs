import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { createInterface } from 'node:readline';
import { once } from 'node:events';
import { fileURLToPath } from 'node:url';

const moduleUrl = new URL('../starters/node/starter.mjs', import.meta.url);

async function setup(t, handler) {
  assert.ok(existsSync(moduleUrl), 'Node persistent starter is missing');
  const { configFromEnv, OrderStore, runOnce } = await import(moduleUrl);
  const directory = mkdtempSync(join(tmpdir(), 'fragment-starter-'));
  const server = createServer(handler);
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const config = configFromEnv({ STARTER_DB: join(directory, 'orders.sqlite'), FRAGMENT_BASE_URL: `http://127.0.0.1:${server.address().port}`, REQUEST_TIMEOUT: '0.1' });
  const store = new OrderStore(config);
  t.after(async () => { store.close(); await new Promise(resolve => server.close(resolve)); rmSync(directory, { recursive: true, force: true }); });
  return { config, store, runOnce, OrderStore, configFromEnv };
}

const selection = { product: 'stars', username: '@completed', amount: 50, payment_method: 'gram' };
function json(response, value, status = 200) {
  response.writeHead(status, { 'Content-Type': 'application/json' });
  response.end(JSON.stringify(value));
}

test('restart polls persisted ID; duplicate receipt and changed selection cannot purchase', async t => {
  let posts = 0;
  const { store, config, runOnce, OrderStore } = await setup(t, (request, response) => {
    if (request.method === 'POST') posts++;
    json(response, { purchase_id: 'remote-1', status: request.method === 'POST' ? 'queued' : 'completed' });
  });
  store.confirmPaid('order-1', selection, 'verified-1');
  assert.throws(() => store.confirmPaid('order-1', { ...selection, amount: 51 }, 'verified-1'));
  assert.throws(() => store.confirmPaid('order-2', selection, 'verified-1'));
  assert.throws(() => store.confirmPaid('order-3', { ...selection, seed: 'not-allowed' }, 'verified-3'));
  await runOnce(store, config, { now: 100 });
  const restarted = new OrderStore(config);
  try {
    restarted.confirmPaid('order-1', selection, 'verified-1');
    await runOnce(restarted, config, { now: 110 });
    await runOnce(restarted, config, { now: 120 });
    assert.equal(restarted.get('order-1').status, 'completed');
    assert.equal(posts, 1);
    assert.ok(!JSON.stringify(restarted.get('order-1')).includes('seed'));
  } finally { restarted.close(); }
});

test('accepted timeout replays stable key', async t => {
  const keys = [];
  const { store, config, runOnce } = await setup(t, async (request, response) => {
    let body = '';
    for await (const chunk of request) body += chunk;
    keys.push(JSON.parse(body).idempotency_key);
    if (keys.length === 1) {
      setTimeout(() => json(response, { purchase_id: 'remote-1', status: 'queued' }), 200);
    } else json(response, { purchase_id: 'remote-1', status: 'completed' });
  });
  store.confirmPaid('order-1', selection, 'verified-1');
  await runOnce(store, config, { now: 100 });
  assert.equal(store.get('order-1').purchase_id, null);
  await runOnce(store, config, { now: 110 });
  assert.equal(store.get('order-1').status, 'completed');
  assert.equal(keys.length, 2);
  assert.equal(keys[0], keys[1]);
});

test('429 observes Retry-After and failure budget stops attempts', async t => {
  const { store, config, runOnce } = await setup(t, (request, response) => {
    response.setHeader('Retry-After', '9');
    json(response, { error: 'rate limited' }, 429);
  });
  store.confirmPaid('order-1', selection, 'verified-1');
  await runOnce(store, config, { now: 100 });
  assert.equal(store.get('order-1').next_attempt, 109);
  for (let now = 200; now <= 500; now += 100) await runOnce(store, config, { now });
  assert.equal(store.get('order-1').status, 'review_required');
  assert.equal(store.claim(3, 600, 10).length, 0);
});

test('concurrency is bounded; abandoned claims recover after lease', async t => {
  let active = 0;
  let peak = 0;
  const { store, config, runOnce } = await setup(t, (request, response) => {
    active++;
    peak = Math.max(peak, active);
    setTimeout(() => { active--; json(response, { purchase_id: 'remote', status: 'queued' }); }, 20);
  });
  for (let i = 0; i < 8; i++) store.confirmPaid(`order-${i}`, selection, `verified-${i}`);
  await runOnce(store, config, { now: 100 });
  assert.equal(peak, config.concurrency);
  assert.equal(store.claim(2, 101, 10).length, 2);
  assert.equal(store.claim(10, 101, 10).length, 3);
  assert.equal(store.claim(10, 101, 10).length, 0);
  assert.equal(store.claim(10, 111, 10).length, 8);
});

test('cancellation preserves lease and never invents failed payment', async t => {
  const { store, config, runOnce } = await setup(t, () => {});
  store.confirmPaid('order-1', selection, 'verified-1');
  const controller = new AbortController();
  const pending = runOnce(store, config, { now: 100, signal: controller.signal });
  setTimeout(() => controller.abort(), 10);
  await assert.rejects(pending);
  assert.equal(store.get('order-1').status, 'pending');
  assert.equal(store.get('order-1').failures, 0);
  assert.equal(store.claim(1, 101, 10).length, 0);
  assert.equal(store.claim(1, 110, 10).length, 1);
});

test('live opt-in and DB environment binding fail closed', async t => {
  const { config, configFromEnv, OrderStore } = await setup(t, () => {});
  for (const env of [{ STARTER_MODE: 'typo' }, { FRAGMENT_BASE_URL: 'https://example.com' }, { STARTER_MODE: 'live' }]) {
    assert.throws(() => configFromEnv(env));
  }
  const live = configFromEnv({ STARTER_MODE: 'live', STARTER_LIVE_CONFIRM: 'I_UNDERSTAND_REAL_PURCHASES', FRAGMENT_BASE_URL: 'https://example.invalid', TON_WALLET_SEED: 'runtime-only', STARTER_SHOP_ID: 'shop', STARTER_DB: config.dbPath });
  assert.throws(() => new OrderStore(live));
});

test('reconciliation is terminal and HTTP errors do not leak bodies', async t => {
  let calls = 0;
  const { store, config, runOnce } = await setup(t, (request, response) => {
    calls++;
    if (calls === 1) json(response, { purchase_id: 'remote', status: 'reconciliation_required' });
    else json(response, { error: 'do-not-persist-this' }, 409);
  });
  store.confirmPaid('order-1', selection, 'verified-1');
  await runOnce(store, config, { now: 100 });
  await runOnce(store, config, { now: 110 });
  assert.equal(calls, 1);
  store.confirmPaid('order-2', selection, 'verified-2');
  await runOnce(store, config, { now: 120 });
  assert.equal(store.get('order-2').status, 'review_required');
  assert.ok(!JSON.stringify(store.get('order-2')).includes('do-not-persist-this'));
});

test('Node worker uses standalone Python mock across deterministic scenarios', { timeout: 15000 }, async t => {
  const { configFromEnv, OrderStore, runOnce } = await import(moduleUrl);
  const directory = mkdtempSync(join(tmpdir(), 'fragment-mock-node-'));
  const child = spawn(process.env.PYTHON ?? 'python3', [fileURLToPath(new URL('../mock_server.py', import.meta.url)), '--port', '0'], { stdio: ['ignore', 'pipe', 'pipe'] });
  const lines = createInterface({ input: child.stdout });
  t.after(async () => {
    lines.close();
    if (child.exitCode === null && child.signalCode === null) { child.kill(); await once(child, 'exit'); }
    rmSync(directory, { recursive: true, force: true });
  });
  const [line] = await Promise.race([
    once(lines, 'line'),
    once(child, 'error').then(([error]) => { throw error; }),
    once(child, 'exit').then(() => { throw new Error('Mock exited before startup'); }),
  ]);
  const config = configFromEnv({ FRAGMENT_BASE_URL: line.split(' ').at(-1), STARTER_DB: join(directory, 'orders.sqlite'), REQUEST_TIMEOUT: '0.1' });
  const store = new OrderStore(config);
  try {
    for (const scenario of ['completed', 'failed', '429', 'timeout', 'reconciliation_required']) {
      store.confirmPaid(scenario, { ...selection, username: '@' + scenario }, 'verified-' + scenario);
    }
    for (const now of [100, 110, 120, 130, 140]) await runOnce(store, config, { now });
    for (const scenario of ['completed', '429', 'timeout']) assert.equal(store.get(scenario).status, 'completed');
    assert.equal(store.get('failed').status, 'failed');
    assert.equal(store.get('reconciliation_required').status, 'reconciliation_required');
  } finally { store.close(); }
});

test('stale claim cannot overwrite a newer result', async t => {
  const { store } = await setup(t, () => {});
  store.confirmPaid('order-1', selection, 'verified-1');
  const [old] = store.claim(1, 100, 10);
  const [fresh] = store.claim(1, 111, 10);
  store.finish(fresh, { status: 'completed', purchaseId: 'new', nextAttempt: 0 });
  store.finish(old, { status: 'failed', purchaseId: 'old', nextAttempt: 0 });
  assert.equal(store.get('order-1').status, 'completed');
  assert.equal(store.get('order-1').purchase_id, 'new');
});

test('shop and order IDs cannot collide at separator', async t => {
  const { config, OrderStore } = await setup(t, () => {});
  const first = new OrderStore({ ...config, shopId: 'shop:part', dbPath: config.dbPath + '.first' });
  const second = new OrderStore({ ...config, shopId: 'shop', dbPath: config.dbPath + '.second' });
  try {
    const one = first.confirmPaid('order', selection, 'verified');
    const two = second.confirmPaid('part:order', selection, 'verified');
    assert.notEqual(one.idempotency_key, two.idempotency_key);
  } finally { first.close(); second.close(); }
});

test('Retry-After starts when response arrives', async t => {
  const { store, config, runOnce } = await setup(t, (request, response) => {
    setTimeout(() => json(response, { error: 'wait', retry_after: 9 }, 429), 50);
  });
  store.confirmPaid('order-1', selection, 'verified');
  await runOnce(store, config);
  assert.ok(store.get('order-1').next_attempt >= Date.now() / 1000 + 8.98);
});
