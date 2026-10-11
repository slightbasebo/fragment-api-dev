import { createHash, randomUUID } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { setTimeout as sleep } from 'node:timers/promises';
import { pathToFileURL } from 'node:url';

const MOCK_SEED = 'mock-only-not-a-wallet';
const SCENARIOS = new Set(['completed', 'failed', '429', 'timeout', 'reconciliation_required']);
const [major, minor] = process.versions.node.split('.').map(Number);
if (major < 22 || (major === 22 && minor < 18)) throw new Error('Node.js 22.18+ is required');

export function configFromEnv(env = process.env) {
  const mode = env.STARTER_MODE ?? 'mock';
  const baseUrl = (env.FRAGMENT_BASE_URL ?? 'http://127.0.0.1:8081').replace(/\/$/, '');
  const url = new URL(baseUrl);
  if (!['mock', 'live'].includes(mode) || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new Error('Use mock/live mode and a bare API origin');
  }
  if (mode === 'mock' && (url.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname))) {
    throw new Error('Mock mode only permits loopback HTTP');
  }
  if (mode === 'live' && (url.protocol !== 'https:' || !env.FRAGMENT_BASE_URL
      || env.STARTER_LIVE_CONFIRM !== 'I_UNDERSTAND_REAL_PURCHASES' || !env.TON_WALLET_SEED?.trim() || !env.STARTER_SHOP_ID?.trim())) {
    throw new Error('Live mode requires explicit HTTPS origin, confirmation, shop ID, and backend wallet seed');
  }
  const concurrency = Number(env.WORKER_CONCURRENCY ?? '3');
  const timeout = Number(env.REQUEST_TIMEOUT ?? '5');
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 16 || !Number.isFinite(timeout) || timeout <= 0 || timeout > 60) {
    throw new Error('Concurrency must be 1-16; timeout must be positive and at most 60 seconds');
  }
  const accountIndex = mode === 'live' && env.TON_ACCOUNT_INDEX ? Number(env.TON_ACCOUNT_INDEX) : undefined;
  if (accountIndex !== undefined && (!Number.isInteger(accountIndex) || accountIndex < 0 || accountIndex > 100)) {
    throw new Error('TON_ACCOUNT_INDEX must be 0-100');
  }
  const config = { mode, baseUrl, dbPath: env.STARTER_DB ?? `orders-node-${mode}.sqlite`, shopId: env.STARTER_SHOP_ID ?? 'demo',
    concurrency, timeout, accountIndex, walletAddress: mode === 'live' ? env.TON_WALLET_ADDRESS : undefined };
  Object.defineProperty(config, 'seed', { value: mode === 'live' ? env.TON_WALLET_SEED : MOCK_SEED, enumerable: false });
  return Object.freeze(config);
}

function validateSelection(selection) {
  const fields = ['amount', 'payment_method', 'product', 'username'];
  if (!selection || Object.keys(selection).sort().join(',') !== fields.join(',')) {
    throw new Error('Only product, username, amount, payment_method are accepted');
  }
  const { product, username, amount, payment_method } = selection;
  if (!['stars', 'premium'].includes(product) || !Number.isSafeInteger(amount)
      || (product === 'stars' && (amount < 50 || amount > 1_000_000))
      || (product === 'premium' && ![3, 6, 12].includes(amount))
      || typeof username !== 'string' || !/^@[A-Za-z0-9_]{1,32}$/.test(username)
      || !['gram', 'usdt'].includes(payment_method)) throw new Error('Invalid order selection');
  return JSON.stringify(Object.fromEntries(fields.map(key => [key, selection[key]])));
}

export class OrderStore {
  constructor(config) {
    this.config = config;
    this.db = new DatabaseSync(config.dbPath);
    this.db.exec(`PRAGMA busy_timeout=5000; PRAGMA journal_mode=WAL;
      CREATE TABLE IF NOT EXISTS context (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS orders (
        order_id TEXT PRIMARY KEY, selection TEXT NOT NULL, payment_reference TEXT NOT NULL UNIQUE,
        idempotency_key TEXT NOT NULL UNIQUE, purchase_id TEXT, status TEXT NOT NULL DEFAULT 'pending',
        failures INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
        lease_until REAL NOT NULL DEFAULT 0, lease_token TEXT, last_error TEXT
      );`);
    const context = JSON.stringify([config.mode, config.baseUrl, config.shopId]);
    this.db.prepare('INSERT OR IGNORE INTO context VALUES (1, ?)').run(context);
    if (this.db.prepare('SELECT value FROM context WHERE id=1').get().value !== context) {
      this.db.close();
      throw new Error('Database belongs to another mode, API origin, or shop; use a separate DB');
    }
  }

  close() { this.db.close(); }

  confirmPaid(orderId, selection, paymentReference) {
    // Trusted backend only: verify provider signature, amount, currency, and final paid state first.
    for (const value of [orderId, paymentReference]) {
      if (typeof value !== 'string' || !/^[A-Za-z0-9_.:-]{1,128}$/.test(value)) throw new Error('Stable order ID and verified payment reference are required');
    }
    const payload = validateSelection(selection);
    const key = 'starter-' + createHash('sha256').update(JSON.stringify([this.config.shopId, orderId])).digest('hex');
    this.db.exec('BEGIN IMMEDIATE');
    try {
      this.db.prepare(`INSERT INTO orders (order_id, selection, payment_reference, idempotency_key)
        VALUES (?, ?, ?, ?) ON CONFLICT(order_id) DO NOTHING`).run(orderId, payload, paymentReference, key);
      const row = this.get(orderId);
      if (row.selection !== payload || row.payment_reference !== paymentReference) throw new Error('Order conflict');
      this.db.exec('COMMIT');
      return row;
    } catch {
      this.db.exec('ROLLBACK');
      throw new Error('Order ID or payment reference already belongs to another selection or payment');
    }
  }

  get(orderId) { return this.db.prepare('SELECT * FROM orders WHERE order_id=?').get(orderId); }

  claim(limit, now, leaseSeconds) {
    return this.db.prepare(`UPDATE orders SET lease_until=?, lease_token=? WHERE order_id IN (
      SELECT order_id FROM orders WHERE status NOT IN ('completed','failed','reconciliation_required','review_required')
      AND next_attempt <= ? AND lease_until <= ? ORDER BY next_attempt, order_id LIMIT ?
    ) RETURNING *`).all(now + leaseSeconds, randomUUID(), now, now, limit);
  }

  finish(row, { status, purchaseId, failures = 0, nextAttempt, error = null }) {
    this.db.prepare(`UPDATE orders SET status=?, purchase_id=?, failures=?, next_attempt=?, last_error=?,
      lease_until=0, lease_token=NULL WHERE order_id=? AND lease_token=?`).run(
      status, purchaseId, failures, nextAttempt, error, row.order_id, row.lease_token);
  }
}

class APIError extends Error {
  constructor(status, retryAfter = 0) {
    super('Fragment request failed');
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

async function request(config, path, payload, signal) {
  const timeout = AbortSignal.timeout(Math.max(1, Math.ceil(config.timeout * 1000)));
  const response = await fetch(config.baseUrl + path, {
    method: payload ? 'POST' : 'GET', redirect: 'error',
    headers: { Accept: 'application/json', ...(payload ? { 'Content-Type': 'application/json' } : {}) },
    body: payload ? JSON.stringify(payload) : undefined,
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
  let body;
  try { body = await response.json(); } catch { throw new APIError(response.status); }
  if (!response.ok) {
    const retry = body?.retry_after ?? Number(response.headers.get('Retry-After'));
    throw new APIError(response.status, Number.isSafeInteger(retry) && retry > 0 ? retry : 0);
  }
  if (!body || typeof body.purchase_id !== 'string' || !body.purchase_id || typeof body.status !== 'string') {
    throw new APIError(502);
  }
  return body;
}

export async function runOnce(store, config, { now, signal } = {}) {
  const currentTime = () => now ?? Date.now() / 1000;
  signal?.throwIfAborted();
  const rows = store.claim(config.concurrency, currentTime(), config.timeout + 5);
  const results = await Promise.allSettled(rows.map(async row => {
    let result;
    try {
      result = row.purchase_id
        ? await request(config, `/api/v1/purchases/${encodeURIComponent(row.purchase_id)}`, undefined, signal)
        : await request(config, '/api/v1/purchases', {
          ...JSON.parse(row.selection), seed: config.seed, idempotency_key: row.idempotency_key,
          ...(config.accountIndex !== undefined ? { account_index: config.accountIndex } : {}),
          ...(config.walletAddress ? { wallet_address: config.walletAddress } : {}),
        }, signal);
    } catch (error) {
      signal?.throwIfAborted(); // Cancellation is not a failed payment; let the lease expire.
      const failures = row.failures + 1;
      const retryable = !(error instanceof APIError) || [429, 500, 502, 503, 504].includes(error.status);
      store.finish(row, { status: retryable && failures < 5 ? row.status : 'review_required', purchaseId: row.purchase_id,
        failures, nextAttempt: currentTime() + Math.max(error.retryAfter ?? 0, Math.min(2 ** failures, 60)),
        error: error instanceof APIError ? `HTTP_${error.status}` : 'TransportError' });
      return;
    }
    store.finish(row, { status: result.status, purchaseId: result.purchase_id, nextAttempt: currentTime() + 2 });
  }));
  const rejected = results.find(result => result.status === 'rejected');
  if (rejected) throw rejected.reason;
}

export async function worker(store, config, signal) {
  while (!signal?.aborted) {
    await runOnce(store, config, { signal });
    await sleep(1000, undefined, { signal });
  }
}

async function main() {
  const config = configFromEnv();
  const store = new OrderStore(config);
  const controller = new AbortController();
  for (const event of ['SIGINT', 'SIGTERM']) process.once(event, () => controller.abort());
  try {
    const [command, orderId, scenario = 'completed'] = process.argv.slice(2);
    if (command === 'demo') {
      if (config.mode !== 'mock' || !SCENARIOS.has(scenario)) throw new Error('Demo accepts mock scenarios only');
      const row = store.confirmPaid(orderId, { product: 'stars', username: '@' + scenario, amount: 50, payment_method: 'gram' }, 'mock:' + orderId);
      console.log(`${row.order_id}: ${row.status}`);
    } else if (command === 'status' && orderId) {
      const row = store.get(orderId);
      console.log(row ? `${row.order_id}: ${row.status}` : 'Order not found');
    } else if (command === 'worker') {
      await worker(store, config, controller.signal);
    } else throw new Error('Usage: node starter.mjs demo ORDER_ID [SCENARIO] | status ORDER_ID | worker');
  } finally { store.close(); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => {
    if (error.name !== 'AbortError') {
      console.error('Starter stopped. Check configuration, command, and persistent order status.');
      process.exitCode = 1;
    }
  });
}
