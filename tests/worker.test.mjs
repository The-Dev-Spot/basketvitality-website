import test, { beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import worker, { cleanProducts } from '../worker/index.js';

const ORIGIN = 'https://basketvitality.com';
let store;
let upstreamCalls;
let upstream;
let logged;

const env = (success = true) => ({
  OFF_SEARCH_LIMIT: { limit: async () => ({ success }) },
  ASSETS: { fetch: async () => new Response('asset') },
});
const ctx = { waitUntil: (promise) => promise };

beforeEach(() => {
  store = new Map();
  upstreamCalls = [];
  logged = [];
  upstream = async () => new Response(JSON.stringify({
    products: [{ code: '123456', product_name: 'Kipfilet', brands: 'Merk', quantity: '500 g', nutriscore_grade: 'b' }],
  }));
  globalThis.fetch = async (url, init) => {
    upstreamCalls.push({ url: String(url), init });
    return upstream();
  };
  globalThis.caches = {
    default: {
      match: async (key) => store.get(key.url)?.clone(),
      put: async (key, response) => { store.set(key.url, response); },
    },
  };
  for (const level of ['log', 'info', 'warn', 'error', 'debug']) {
    console[level] = (...args) => logged.push(args);
  }
});

function post(q, headers = {}, raw) {
  return new Request(`${ORIGIN}/api/off-search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Sec-Fetch-Site': 'same-origin', ...headers },
    body: raw ?? JSON.stringify({ q }),
  });
}

test('returns cleaned products and identifies itself upstream', async () => {
  const response = await worker.fetch(post('Kipfilet'), env(), ctx);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.deepEqual(body.products[0], { barcode: '123456', name: 'Kipfilet', brand: 'Merk', quantity: '500 g', grade: 'B' });
  assert.match(body.attribution, /Open Food Facts/);
  assert.match(upstreamCalls[0].init.headers['User-Agent'], /^BasketVitality-Website\/1\.0 \(/);
  assert.match(upstreamCalls[0].url, /search_terms=kipfilet/);
});

test('sends nothing about the visitor upstream', async () => {
  await worker.fetch(post('kipfilet', { 'CF-Connecting-IP': '203.0.113.9', Cookie: 'a=b' }), env(), ctx);
  assert.deepEqual(Object.keys(upstreamCalls[0].init.headers).sort(), ['Accept', 'User-Agent']);
  assert.doesNotMatch(upstreamCalls[0].url, /203\.0\.113\.9/);
});

test('a repeated search uses the cache, and the key does not contain the text', async () => {
  await worker.fetch(post('kipfilet'), env(), ctx);
  const response = await worker.fetch(post('  KIPFILET '), env(), ctx);
  assert.equal(response.status, 200);
  assert.equal(upstreamCalls.length, 1);
  assert.doesNotMatch([...store.keys()][0], /kipfilet/);
});

test('the cap returns busy without calling upstream', async () => {
  const response = await worker.fetch(post('kipfilet'), env(false), ctx);
  assert.equal(response.status, 429);
  assert.equal(upstreamCalls.length, 0);
});

test('upstream failure returns a clean error and is not cached', async () => {
  upstream = async () => new Response('nope', { status: 503 });
  const first = await worker.fetch(post('kipfilet'), env(), ctx);
  assert.equal(first.status, 503);
  upstream = async () => { throw new Error('network'); };
  const second = await worker.fetch(post('kipfilet'), env(), ctx);
  assert.equal(second.status, 503);
  upstream = async () => new Response('not json');
  const third = await worker.fetch(post('kipfilet'), env(), ctx);
  assert.equal(third.status, 503);
  assert.equal(store.size, 0);
});

test('cross-site requests are refused', async () => {
  const response = await worker.fetch(post('kipfilet', { 'Sec-Fetch-Site': 'cross-site' }), env(), ctx);
  assert.equal(response.status, 403);
  assert.equal(upstreamCalls.length, 0);
});

test('bad input is refused before anything is sent', async () => {
  for (const q of ['', 'a', '<script>', 'x'.repeat(81), 42]) {
    assert.equal((await worker.fetch(post(q), env(), ctx)).status, 400);
  }
  assert.equal((await worker.fetch(post('', {}, 'not json'), env(), ctx)).status, 400);
  assert.equal((await worker.fetch(post('', {}, JSON.stringify({ q: 'a'.repeat(600) })), env(), ctx)).status, 413);
  assert.equal((await worker.fetch(post('kip', { 'Content-Type': 'text/plain' }), env(), ctx)).status, 415);
  assert.equal(upstreamCalls.length, 0);
});

test('only POST is accepted, other api paths are 404, and other paths go to assets', async () => {
  const get = await worker.fetch(new Request(`${ORIGIN}/api/off-search?q=kip`), env(), ctx);
  assert.equal(get.status, 405);
  assert.equal(get.headers.get('Allow'), 'POST');
  assert.equal((await worker.fetch(new Request(`${ORIGIN}/api/other`), env(), ctx)).status, 404);
  assert.equal(await (await worker.fetch(new Request(`${ORIGIN}/`), env(), ctx)).text(), 'asset');
});

test('the Worker logs nothing', async () => {
  await worker.fetch(post('geheim product'), env(), ctx);
  upstream = async () => { throw new Error('network'); };
  await worker.fetch(post('ander product'), env(), ctx);
  assert.deepEqual(logged, []);
});

test('responses are not cacheable by the browser', async () => {
  const response = await worker.fetch(post('kipfilet'), env(), ctx);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  assert.equal(response.headers.get('X-Content-Type-Options'), 'nosniff');
});

test('product cleaning drops unknown grades, bad barcodes and nameless rows', () => {
  const cleaned = cleanProducts({ products: [
    { code: '12<script>', product_name: ' Naam\n  twee ', nutriscore_grade: 'not-applicable' },
    { code: '123456', nutriscore_grade: 'a' },
    { code: '123456', product_name_nl: 'Nederlands', product_name: 'English', nutriscore_grade: 'E' },
  ] });
  assert.deepEqual(cleaned, [
    { barcode: '', name: 'Naam twee', brand: '', quantity: '', grade: null },
    { barcode: '123456', name: 'Nederlands', brand: '', quantity: '', grade: 'E' },
  ]);
  assert.deepEqual(cleanProducts({}), []);
});
