// Search logic for the shopping-list checker. No DOM and no network, so it can
// be tested directly. Product data comes from Open Food Facts contributors and
// is treated as untrusted text: callers must only ever render it as text.

const QUANTITY = /^\d+(?:[.,]\d+)?(?:x|st|stuks?|g|gr|gram|kg|kilo|l|liter|ml|cl)?$/;
const MAX_LINES = 50;
const MIN_EXACT = 3;
const MOSTLY_SHARE = 0.75;
export const MAX_CHOICES = 8;

export function normalise(text) {
  return String(text)
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .toLowerCase();
}

export function tokens(text) {
  return normalise(text).match(/[\p{L}\p{N}]+/gu) ?? [];
}

export function queryTokens(line) {
  return tokens(line).filter((token) => !QUANTITY.test(token) && token !== 'x');
}

export function prepare(rows) {
  return rows.map(([barcode, name, brand, quantity, grade, flag]) => {
    const words = new Set([...tokens(name), ...tokens(brand)]);
    if (words.has('albert') && words.has('heijn')) words.add('ah');
    if (words.has('ah')) {
      words.add('albert');
      words.add('heijn');
    }
    return { barcode, name, brand, quantity, grade, flag, words, nameKey: tokens(name).join(' ') };
  });
}

function compare(a, b, key) {
  const rank = (product) => {
    if (product.nameKey === key) return 0;
    if (product.nameKey.startsWith(`${key} `)) return 1;
    if (product.nameKey.includes(key)) return 2;
    return 3;
  };
  return rank(a) - rank(b)
    || a.flag - b.flag
    || a.name.length - b.name.length
    || a.name.localeCompare(b.name, 'nl')
    || a.barcode.localeCompare(b.barcode);
}

// Whole words first. Part-word matches only when nothing else matched, and only
// for longer words, so "kaas" finds "pindakaas" only if nothing is called kaas.
export function search(products, line) {
  const query = queryTokens(line);
  if (query.length === 0) return [];
  const key = query.join(' ');
  let hits = products.filter((product) => query.every((token) => product.words.has(token)));
  if (hits.length === 0 && query.every((token) => token.length >= 4)) {
    hits = products.filter((product) => query.every((token) => product.nameKey.includes(token)));
  }
  return hits.sort((a, b) => compare(a, b, key));
}

export function gradeCounts(hits) {
  const counts = { A: 0, B: 0, C: 0, D: 0, E: 0 };
  for (const hit of hits) counts[hit.grade] += 1;
  return counts;
}

// One line of the list becomes one of:
//   empty      nothing to search for, for example "2x"
//   missing    no product matched
//   resolved   one product, or a product the visitor chose
//   uniform    several products that all have the same grade
//   mostly     at least 75% of the products named like this share one grade
//   range      grades differ too much to count one, so the visitor must choose
//
// When at least three products are named exactly what was typed, only those set
// the grade. That keeps "havermout" from being judged by chocolate oat sticks.
// Every match stays available as a choice.
export function evaluateLine(products, line, chosen = null) {
  if (queryTokens(line).length === 0) return { line, status: 'empty' };
  if (chosen) return { line, status: 'resolved', grade: chosen.grade, product: chosen, hits: [] };
  const hits = search(products, line);
  if (hits.length === 0) return { line, status: 'missing', hits };
  if (hits.length === 1) return { line, status: 'resolved', grade: hits[0].grade, product: hits[0], hits };
  const key = queryTokens(line).join(' ');
  const exact = hits.filter((hit) => hit.nameKey === key);
  const basis = exact.length >= MIN_EXACT ? exact : hits;
  const counts = gradeCounts(basis);
  const present = Object.keys(counts).filter((grade) => counts[grade] > 0);
  const total = basis.length;
  if (present.length === 1) return { line, status: 'uniform', grade: present[0], counts, total, hits };
  const top = present.reduce((best, grade) => (counts[grade] > counts[best] ? grade : best));
  if (total >= MIN_EXACT && counts[top] / total >= MOSTLY_SHARE) {
    return { line, status: 'mostly', grade: top, topCount: counts[top], counts, total, hits };
  }
  return { line, status: 'range', low: present[0], high: present[present.length - 1], counts, total, hits };
}

export function parseList(text) {
  return String(text)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, MAX_LINES);
}

export function summarise(results) {
  const items = results.filter((result) => result.status !== 'empty');
  const scored = items.filter((result) => result.grade);
  return {
    total: items.length,
    scored: scored.length,
    low: scored.filter((result) => result.grade === 'D' || result.grade === 'E').length,
    choose: items.filter((result) => result.status === 'range').length,
    missing: items.filter((result) => result.status === 'missing').length,
    unscored: items.filter((result) => result.status === 'resolved' && !result.grade).length,
  };
}
