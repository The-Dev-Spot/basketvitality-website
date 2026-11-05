// Guards the promises the site makes about itself.
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';

const tracked = execFileSync('git', ['ls-files'], { encoding: 'utf8' }).split('\n').filter(Boolean);
const pages = tracked.filter((file) => file.endsWith('.html'));
const scripted = new Set(['checker/index.html', 'nl/lijst-checker/index.html']);
const read = (file) => readFileSync(file, 'utf8');
const ignored = read('.assetsignore').split('\n').map((line) => line.trim()).filter((line) => line && !line.startsWith('#'));

test('only the checker pages run script, and only from this site', () => {
  for (const page of pages) {
    const scripts = [...read(page).matchAll(/<script\b([^>]*)>/gi)].map((match) => match[1]);
    const executable = scripts.filter((attrs) => !/type=["']application\/ld\+json["']/i.test(attrs));
    if (scripted.has(page)) {
      assert.deepEqual(executable.map((attrs) => attrs.trim()), ['type="module" src="/checker.js"'], page);
    } else {
      assert.deepEqual(executable, [], page);
    }
  }
});

test('no page loads anything from another site', () => {
  for (const page of pages) {
    const html = read(page);
    for (const match of html.matchAll(/<(?:script|img|iframe)\b[^>]*\bsrc=["'](?:https?:)?\/\/[^"']+/gi)) {
      assert.fail(`${page}: ${match[0]}`);
    }
    for (const match of html.matchAll(/<link\b[^>]*>/gi)) {
      const stylesheet = /rel=["']stylesheet["']/i.test(match[0]);
      assert.ok(!stylesheet || !/href=["'](?:https?:)?\/\//i.test(match[0]), `${page}: ${match[0]}`);
    }
  }
});

test('every page that shows product data credits Open Food Facts', () => {
  for (const page of pages.filter((file) => !file.startsWith('privacy/'))) {
    assert.match(read(page), /Open Food Facts/, page);
  }
});

test('the checker pages have their own script policy, and everything else denies script', () => {
  const headers = read('_headers');
  const global = headers.split('\n').find((line) => line.trim().startsWith('Content-Security-Policy: default-src'));
  assert.doesNotMatch(global, /script-src/);
  for (const path of ['/checker/*', '/nl/lijst-checker/*']) {
    const start = headers.indexOf(`${path}\n`);
    assert.notEqual(start, -1, path);
    const block = headers.slice(start, headers.indexOf('\n\n', start));
    assert.match(block, /! Content-Security-Policy/);
    assert.match(block, /script-src 'self'; connect-src 'self'/);
    assert.doesNotMatch(block, /https?:/);
  }
});

test('non-site files are never served', () => {
  for (const entry of ['.git', '.github', 'worker', 'scripts', 'tests', 'package.json', 'wrangler.jsonc']) {
    assert.ok(ignored.includes(entry), entry);
  }
});

// ---- Search guards ---------------------------------------------------------

const decode = (text) => text.replaceAll('&amp;', '&').replaceAll('&#x27;', "'").replaceAll('&quot;', '"');
const indexable = pages.filter((file) => !file.endsWith('404.html'));
const urlOf = (file) => `/${file.replace(/index\.html$/, '')}`;
const meta = (html, pattern) => html.match(pattern)?.[1];
const sitemap = [...read('sitemap.xml').matchAll(/<loc>https:\/\/basketvitality\.com([^<]*)<\/loc>/g)].map((match) => match[1]);

test('every page has one h1, a useful title and a useful description', () => {
  for (const page of pages) {
    const html = read(page);
    assert.equal((html.match(/<h1\b/g) ?? []).length, 1, `${page}: h1`);
    const title = decode(meta(html, /<title>([^<]*)<\/title>/) ?? '');
    const description = decode(meta(html, /<meta name="description" content="([^"]*)"/) ?? '');
    assert.ok(title.length >= 20 && title.length <= 68, `${page}: title is ${title.length}: ${title}`);
    assert.ok(description.length >= 70 && description.length <= 165, `${page}: description is ${description.length}: ${description}`);
  }
});

test('titles and descriptions are unique', () => {
  for (const pattern of [/<title>([^<]*)<\/title>/, /<meta name="description" content="([^"]*)"/]) {
    const seen = new Map();
    for (const page of pages) {
      const value = meta(read(page), pattern);
      assert.ok(!seen.has(value), `${page} repeats ${seen.get(value)}: ${value}`);
      seen.set(value, page);
    }
  }
});

test('every indexable page points to itself as canonical', () => {
  for (const page of indexable) {
    const canonical = meta(read(page), /<link rel="canonical" href="([^"]*)"/);
    assert.equal(canonical, `https://basketvitality.com${urlOf(page)}`, page);
  }
});

test('language versions point to each other', () => {
  const alternates = (page) => Object.fromEntries(
    [...read(page).matchAll(/<link rel="alternate" hreflang="([^"]+)" href="https:\/\/basketvitality\.com([^"]*)"/g)].map((m) => [m[1], m[2]]));
  for (const page of indexable.filter((file) => !file.startsWith('privacy/'))) {
    const links = alternates(page);
    assert.ok(links.en && links.nl, page);
    assert.ok([links.en, links.nl].includes(urlOf(page)), `${page}: doesn't list itself`);
    const other = links.en === urlOf(page) ? links.nl : links.en;
    assert.deepEqual(alternates(`${other.slice(1)}index.html`), links, page);
    assert.equal(links['x-default'], links.en, page);
  }
});

test('the sitemap lists every indexable page and nothing else', () => {
  assert.deepEqual([...sitemap].sort(), indexable.map(urlOf).sort());
  assert.equal((read('sitemap.xml').match(/<lastmod>\d{4}-\d{2}-\d{2}<\/lastmod>/g) ?? []).length, sitemap.length);
});

test('robots.txt allows crawling and names the sitemap', () => {
  const robots = read('robots.txt');
  assert.match(robots, /^Allow: \/$/m);
  assert.doesNotMatch(robots, /^Disallow: \/$/m);
  assert.match(robots, /^Sitemap: https:\/\/basketvitality\.com\/sitemap\.xml$/m);
});

test('404 pages are not indexed and are served', () => {
  for (const page of ['404.html', 'nl/404.html']) {
    const html = read(page);
    assert.match(html, /<meta name="robots" content="noindex">/);
    assert.doesNotMatch(html, /rel="canonical"/);
  }
  assert.match(read('wrangler.jsonc'), /"not_found_handling": "404-page"/);
});

test('production is only served from the canonical domain', () => {
  assert.match(read('wrangler.jsonc'), /"workers_dev": false/);
});

test('structured data parses and describes the page it is on', () => {
  for (const page of pages) {
    const html = read(page);
    const blocks = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((match) => JSON.parse(match[1].replaceAll('<\\/', '</')));
    if (page.endsWith('404.html') || page.startsWith('privacy/') || page.includes('roadmap/')) continue;
    assert.ok(blocks.length > 0, page);
    for (const block of blocks) assert.equal(block['@context'], 'https://schema.org', page);
    const crumbs = blocks.find((block) => block['@type'] === 'BreadcrumbList');
    if (crumbs) {
      assert.equal(crumbs.itemListElement.at(-1).item, `https://basketvitality.com${urlOf(page)}`, page);
      assert.match(html, /class="wrap breadcrumbs"/, page);
    }
  }
});

test('FAQ data matches the questions on the page', () => {
  for (const page of ['receipt-scanning/index.html', 'nl/kassabon-scannen/index.html']) {
    const html = read(page);
    const data = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map((m) => JSON.parse(m[1])).find((b) => b['@type'] === 'FAQPage');
    for (const entry of data.mainEntity) assert.ok(html.includes(`<h3>${entry.name}</h3>`), `${page}: ${entry.name}`);
  }
});

test('internal links and assets resolve', () => {
  const exists = (url) => {
    const clean = url.split(/[?#]/)[0];
    return clean === '' || tracked.includes(clean.endsWith('/') ? `${clean.slice(1)}index.html` : clean.slice(1));
  };
  for (const page of pages) {
    for (const match of read(page).matchAll(/(?:href|src)="(\/(?!\/)[^"]*)"/g)) {
      assert.ok(exists(match[1]), `${page}: ${match[1]}`);
    }
  }
  for (const sheet of ['roadmap.css', ...pages]) {
    for (const match of read(sheet).matchAll(/url\("(\/fonts\/[^"]+)"\)/g)) {
      assert.ok(exists(match[1]), `${sheet}: ${match[1]}`);
    }
  }
});

test('no tracker or analytics is loaded for search setup', () => {
  for (const page of pages) {
    assert.doesNotMatch(read(page), /googletagmanager|google-analytics|gtag\(|fbq\(|clarity\.ms|plausible|cloudflareinsights/i, page);
  }
});

test('every page has the shared footer with the business details the law requires', () => {
  for (const page of pages) {
    const html = read(page);
    assert.match(html, /<link rel="stylesheet" href="\/footer\.css">/, page);
    assert.equal((html.match(/<footer class="site-footer">/g) ?? []).length, 1, page);
    const footer = html.slice(html.indexOf('<footer'));
    for (const detail of [/Westerstraat 10 UNIT G4118/, /(?:KVK|KvK) 42149955/, /NL005535532B67/, /privacy@basketvitality\.com/, /Open Food Facts/]) {
      assert.match(footer, detail, `${page}: ${detail}`);
    }
  }
});
