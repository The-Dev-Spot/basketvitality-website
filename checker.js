// Shopping-list checker UI (HOM-2026, HOM-2027).
// The list stays in this page's memory. It is not stored, and nothing is sent
// unless the visitor taps "Search online" for one item.
// Everything is rendered with textContent, because product data is untrusted.

import { MAX_CHOICES, evaluateLine, parseList, prepare, queryTokens, summarise } from './checker-core.js';

const INDEX_URL = '/data/products-nl-2026-07.json';
const SEARCH_URL = '/api/off-search';

const TEXT = {
  en: {
    loading: 'Loading the product list…',
    loadFailed: "The product list didn't load. Check your connection and try again.",
    empty: 'Add at least one product, one per line.',
    headline: (low, scored) => `${low} of ${scored} scored ${scored === 1 ? 'item' : 'items'} got a D or E.`,
    noScored: 'None of these items has a score yet.',
    pick: (n) => `Choose a product for ${n} ${n === 1 ? 'item' : 'items'} to include ${n === 1 ? 'it' : 'them'}.`,
    missing: (n) => `${n} ${n === 1 ? "wasn't" : "weren't"} found.`,
    noScoreCount: (n) => `${n} ${n === 1 ? 'has' : 'have'} no score yet.`,
    range: (low, high, n) => `Scores from ${low} to ${high} across ${n} products. Choose yours to count it.`,
    uniform: (n) => `All ${n} products with this name score the same.`,
    mostly: (grade, top, n) => `Mostly ${grade}: ${top} of ${n} products with this name. Choose yours if you know it.`,
    notFound: 'Not found in our product list.',
    noScore: 'No score yet',
    choose: 'Choose a product',
    notListed: 'Not listed?',
    change: 'Change product',
    searchOnline: 'Search online',
    searchNote: "This sends only this item's text to our server, which asks Open Food Facts. We don't store it with anything about you.",
    searching: 'Searching Open Food Facts…',
    noResults: 'Open Food Facts found nothing for this item.',
    busy: "Online search isn't available right now.",
    tryThere: 'Search on Open Food Facts',
    fromOnline: 'Result from Open Food Facts',
    warning: 'Check the pack: the nutrition values in this record look inconsistent.',
    badgeNone: 'No score',
    badgeMissing: 'Not found',
    badgePick: 'Several scores',
    use: 'Use',
    record: 'View the record',
    grade: (grade) => `Nutri-Score ${grade}`,
  },
  nl: {
    loading: 'Productlijst laden…',
    loadFailed: 'De productlijst is niet geladen. Controleer je verbinding en probeer het opnieuw.',
    empty: 'Voeg minstens één product toe, één per regel.',
    headline: (low, scored) => `${low} van ${scored} ${scored === 1 ? 'product' : 'producten'} met een score ${low === 1 ? 'kreeg' : 'kregen'} een D of E.`,
    noScored: 'Geen van deze producten heeft al een score.',
    pick: (n) => `Kies een product bij ${n} ${n === 1 ? 'regel' : 'regels'} om ${n === 1 ? 'die' : 'ze'} mee te tellen.`,
    missing: (n) => `${n} niet gevonden.`,
    noScoreCount: (n) => `${n} nog zonder score.`,
    range: (low, high, n) => `Scores van ${low} tot ${high} bij ${n} producten. Kies het jouwe om het mee te tellen.`,
    uniform: (n) => `Alle ${n} producten met deze naam hebben dezelfde score.`,
    mostly: (grade, top, n) => `Meestal ${grade}: ${top} van de ${n} producten met deze naam. Kies het jouwe als je het weet.`,
    notFound: 'Niet gevonden in onze productlijst.',
    noScore: 'Nog geen score',
    choose: 'Kies een product',
    notListed: 'Staat het er niet bij?',
    change: 'Ander product kiezen',
    searchOnline: 'Online zoeken',
    searchNote: 'Dit stuurt alleen de tekst van deze regel naar onze server, die het aan Open Food Facts vraagt. We bewaren het niet samen met iets over jou.',
    searching: 'Zoeken bij Open Food Facts…',
    noResults: 'Open Food Facts vond niets voor deze regel.',
    busy: 'Online zoeken lukt nu niet.',
    tryThere: 'Zoek op Open Food Facts',
    fromOnline: 'Resultaat van Open Food Facts',
    warning: 'Controleer de verpakking: de voedingswaarden in dit record lijken niet te kloppen.',
    badgeNone: 'Geen score',
    badgeMissing: 'Niet gevonden',
    badgePick: 'Meerdere scores',
    use: 'Kies',
    record: 'Bekijk het record',
    grade: (grade) => `Nutri-Score ${grade}`,
  },
};

const t = TEXT[document.documentElement.lang] ?? TEXT.en;
const form = {
  input: document.getElementById('list'),
  check: document.getElementById('check'),
  example: document.getElementById('example'),
  status: document.getElementById('status'),
  summary: document.getElementById('summary'),
  results: document.getElementById('results'),
};

let products = null;
let lines = [];
const chosen = new Map();
const online = new Map();

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function offSearchUrl(query) {
  const params = new URLSearchParams({ search_terms: query, search_simple: '1', action: 'process' });
  return `https://nl.openfoodfacts.org/cgi/search.pl?${params}`;
}

function externalLink(href, text) {
  const link = el('a', 'text-link', text);
  link.href = href;
  link.rel = 'noopener noreferrer';
  link.target = '_blank';
  return link;
}

function productLabel(product) {
  return [product.name, product.brand, product.quantity].filter(Boolean).join(' · ');
}

function badge(result) {
  if (result.grade) {
    const chip = el('span', `grade ${result.grade.toLowerCase()}`, result.grade);
    chip.setAttribute('aria-label', t.grade(result.grade));
    return chip;
  }
  const label = result.status === 'range' ? t.badgePick : result.status === 'missing' ? t.badgeMissing : t.badgeNone;
  const chip = el('span', 'grade none', result.status === 'range' ? '…' : '?');
  chip.setAttribute('aria-label', label);
  return chip;
}

function choiceList(index, options, heading, footer = null) {
  const details = el('details', 'choices');
  details.append(el('summary', '', heading));
  const list = el('ul');
  for (const option of options) {
    const row = el('li');
    const use = el('button', 'choice');
    use.type = 'button';
    const letter = option.grade
      ? el('span', `grade small ${option.grade.toLowerCase()}`, option.grade)
      : el('span', 'grade small none', '?');
    letter.setAttribute('aria-label', option.grade ? t.grade(option.grade) : t.badgeNone);
    use.append(letter, el('span', '', productLabel(option)));
    use.addEventListener('click', () => {
      chosen.set(index, option);
      render();
    });
    row.append(use);
    list.append(row);
  }
  details.append(list);
  if (footer) details.append(footer);
  return details;
}

function onlineBlock(index, line) {
  const box = el('div', 'online');
  const query = queryTokens(line).join(' ');
  const state = online.get(index);
  if (!state) {
    const button = el('button', 'btn-quiet', t.searchOnline);
    button.type = 'button';
    button.addEventListener('click', () => searchOnline(index, line));
    box.append(button, el('p', 'fine', t.searchNote));
  } else if (state.status === 'loading') {
    box.append(el('p', 'fine', t.searching));
  } else if (state.status === 'failed') {
    const note = el('p', 'fine', `${t.busy} `);
    note.append(externalLink(offSearchUrl(query), t.tryThere));
    box.append(note);
  } else if (state.products.length === 0) {
    const note = el('p', 'fine', `${t.noResults} `);
    note.append(externalLink(offSearchUrl(query), t.tryThere));
    box.append(note);
  } else {
    const details = choiceList(index, state.products.map((p) => ({ ...p, flag: 0, online: true })), t.fromOnline);
    details.open = true;
    box.append(details);
  }
  return box;
}

function productChoices(index, result) {
  const footer = el('div');
  footer.append(el('p', 'fine not-listed', t.notListed), onlineBlock(index, result.line));
  const details = choiceList(index, result.hits.slice(0, MAX_CHOICES), t.choose, footer);
  if (online.has(index)) details.open = true;
  return details;
}

function resultRow(result, index) {
  const row = el('li', 'result');
  row.append(badge(result));
  const body = el('div', 'result-body');
  row.append(body);

  const title = result.product ? productLabel(result.product) : result.line;
  body.append(el('p', 'result-title', title));

  if (result.status === 'resolved') {
    if (!result.grade) body.append(el('p', 'fine', t.noScore));
    if (result.product.online) body.append(el('p', 'fine', t.fromOnline));
    if (result.product.flag === 2) body.append(el('p', 'warn', t.warning));
    if (result.product.barcode) {
      const line = el('p', 'fine');
      line.append(externalLink(`https://nl.openfoodfacts.org/product/${encodeURIComponent(result.product.barcode)}`, t.record));
      body.append(line);
    }
    if (chosen.has(index)) {
      const change = el('button', 'link-button', t.change);
      change.type = 'button';
      change.addEventListener('click', () => {
        chosen.delete(index);
        render();
      });
      body.append(change);
    }
  } else if (result.status === 'uniform') {
    body.append(el('p', 'fine', t.uniform(result.total)));
    body.append(productChoices(index, result));
  } else if (result.status === 'mostly') {
    body.append(el('p', 'fine', t.mostly(result.grade, result.topCount, result.total)));
    body.append(productChoices(index, result));
  } else if (result.status === 'range') {
    body.append(el('p', 'fine', t.range(result.low, result.high, result.total)));
    body.append(productChoices(index, result));
  } else if (result.status === 'missing') {
    body.append(el('p', 'fine', t.notFound));
    body.append(onlineBlock(index, result.line));
  }
  return row;
}

function render() {
  const results = lines.map((line, index) => evaluateLine(products, line, chosen.get(index) ?? null));
  const summary = summarise(results);
  form.results.replaceChildren(...results
    .map((result, index) => (result.status === 'empty' ? null : resultRow(result, index)))
    .filter(Boolean));

  form.summary.replaceChildren();
  if (summary.total === 0) {
    form.status.textContent = t.empty;
    form.summary.hidden = true;
    return;
  }
  form.status.textContent = '';
  form.summary.hidden = false;
  form.summary.append(el('h2', '', summary.scored > 0 ? t.headline(summary.low, summary.scored) : t.noScored));
  const notes = [];
  if (summary.choose) notes.push(t.pick(summary.choose));
  if (summary.unscored) notes.push(t.noScoreCount(summary.unscored));
  if (summary.missing) notes.push(t.missing(summary.missing));
  if (notes.length) form.summary.append(el('p', '', notes.join(' ')));
}

async function loadProducts() {
  if (products) return true;
  form.status.textContent = t.loading;
  try {
    const response = await fetch(INDEX_URL);
    if (!response.ok) throw new Error('index');
    products = prepare((await response.json()).products);
    return true;
  } catch {
    form.status.textContent = t.loadFailed;
    return false;
  }
}

async function check() {
  form.check.disabled = true;
  const ready = await loadProducts();
  form.check.disabled = false;
  if (!ready) return;
  lines = parseList(form.input.value);
  chosen.clear();
  online.clear();
  render();
  if (lines.length) form.summary.focus();
}

async function searchOnline(index, line) {
  online.set(index, { status: 'loading' });
  render();
  try {
    const response = await fetch(SEARCH_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: queryTokens(line).join(' ') }),
    });
    if (!response.ok) throw new Error('search');
    const body = await response.json();
    online.set(index, { status: 'done', products: body.products ?? [] });
  } catch {
    online.set(index, { status: 'failed' });
  }
  render();
}

form.check.addEventListener('click', check);
form.example.addEventListener('click', () => {
  form.input.value = form.example.dataset.list.replaceAll('|', '\n');
  check();
});
