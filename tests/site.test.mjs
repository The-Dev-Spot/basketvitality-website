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
