// Online search for the shopping-list checker (HOM-2027).
//
// The visitor taps "Search online" and the browser posts one item here. This
// Worker asks Open Food Facts and returns a short, cleaned list. It exists so
// that the visitor's IP never reaches a third party and the page's CSP can stay
// connect-src 'self'.
//
// Privacy rules for this file:
//  - Never log the search text or anything about the visitor.
//  - POST, so the text is not in a URL.
//  - The cache key is a hash and the cached value holds results only.
// Everything else on the site is served as static assets and never reaches this code.

const UPSTREAM = 'https://nl.openfoodfacts.org/cgi/search.pl';
const USER_AGENT = 'BasketVitality-Website/1.0 (feedback@basketvitality.com)';
const CACHE_SECONDS = 86400;
const MAX_BODY = 512;
const MAX_RESULTS = 8;
const GRADES = new Set(['a', 'b', 'c', 'd', 'e']);
const ALLOWED = /^[\p{L}\p{N} .,'&%+\-]{2,80}$/u;

const HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'",
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Referrer-Policy': 'no-referrer',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
};

function reply(status, body, extra = {}) {
  return new Response(JSON.stringify(body), { status, headers: { ...HEADERS, ...extra } });
}

function isSameOrigin(request, url) {
  const site = request.headers.get('Sec-Fetch-Site');
  if (site) return site === 'same-origin';
  const origin = request.headers.get('Origin');
  return origin === url.origin;
}

function text(value, limit) {
  return typeof value === 'string' ? value.replace(/\s+/g, ' ').trim().slice(0, limit) : '';
}

export function cleanProducts(payload) {
  const products = Array.isArray(payload?.products) ? payload.products : [];
  return products
    .map((product) => {
      const grade = text(product.nutriscore_grade, 1).toLowerCase();
      return {
        barcode: /^\d{4,14}$/.test(String(product.code)) ? String(product.code) : '',
        name: text(product.product_name_nl, 90) || text(product.product_name, 90),
        brand: text(product.brands, 50),
        quantity: text(product.quantity, 24),
        grade: GRADES.has(grade) ? grade.toUpperCase() : null,
      };
    })
    .filter((product) => product.name)
    .slice(0, MAX_RESULTS);
}

async function cacheKey(query, url) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(query));
  const hex = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
  return new Request(`${url.origin}/__off-search-cache/${hex}`);
}

function upstreamUrl(query) {
  const params = new URLSearchParams({
    search_terms: query,
    search_simple: '1',
    action: 'process',
    json: '1',
    page_size: String(MAX_RESULTS),
    fields: 'code,product_name,product_name_nl,brands,quantity,nutriscore_grade',
  });
  return `${UPSTREAM}?${params}`;
}

async function search(request, env, ctx, url) {
  if (!isSameOrigin(request, url)) return reply(403, { error: 'forbidden' });
  if (!(request.headers.get('Content-Type') ?? '').startsWith('application/json')) {
    return reply(415, { error: 'unsupported' });
  }

  const raw = await request.text();
  if (raw.length > MAX_BODY) return reply(413, { error: 'too-large' });
  let query;
  try {
    query = JSON.parse(raw).q;
  } catch {
    return reply(400, { error: 'invalid' });
  }
  if (typeof query !== 'string') return reply(400, { error: 'invalid' });
  query = query.normalize('NFC').replace(/\s+/g, ' ').trim().toLowerCase();
  if (!ALLOWED.test(query)) return reply(400, { error: 'invalid' });

  const key = await cacheKey(query, url);
  const cached = await caches.default.match(key);
  if (cached) return reply(200, await cached.json());

  // Open Food Facts allows 10 searches a minute per IP. All visitors share this
  // Worker, so the cap protects them from being blocked. See wrangler.jsonc.
  const { success } = await env.OFF_SEARCH_LIMIT.limit({ key: 'off-search' });
  if (!success) return reply(429, { error: 'busy' }, { 'Retry-After': '60' });

  let upstream;
  try {
    upstream = await fetch(upstreamUrl(query), {
      headers: { 'User-Agent': USER_AGENT, Accept: 'application/json' },
      signal: AbortSignal.timeout(6000),
    });
  } catch {
    return reply(503, { error: 'unavailable' });
  }
  if (!upstream.ok) return reply(503, { error: 'unavailable' });

  let payload;
  try {
    payload = await upstream.json();
  } catch {
    return reply(503, { error: 'unavailable' });
  }

  const body = {
    products: cleanProducts(payload),
    attribution: '© Open Food Facts contributors, ODbL v1.0',
  };
  ctx.waitUntil(caches.default.put(key, new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json', 'Cache-Control': `public, max-age=${CACHE_SECONDS}` },
  })));
  return reply(200, body);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (url.pathname === '/api/off-search') {
      if (request.method !== 'POST') return reply(405, { error: 'method' }, { Allow: 'POST' });
      return search(request, env, ctx, url);
    }
    if (url.pathname.startsWith('/api/')) return reply(404, { error: 'not-found' });
    return env.ASSETS.fetch(request);
  },
};
