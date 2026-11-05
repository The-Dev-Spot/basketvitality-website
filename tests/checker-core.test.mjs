import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateLine, parseList, prepare, queryTokens, search, summarise } from '../checker-core.js';

const rows = [
  ['1', 'Havermout', 'Albert Heijn', '500 g', 'A', 0],
  ['2', 'Havermout chocolade', 'Merk', '', 'C', 2],
  ['3', 'Pindakaas', 'Merk', '', 'B', 0],
  ['4', 'Crème fraîche', 'Merk', '', 'E', 0],
  ['5', 'Zwarte koffie', 'Merk', '', 'A', 0],
  ['6', 'Espresso koffie', 'Merk', '', 'A', 0],
];
const products = prepare(rows);

test('quantities are ignored, words are kept', () => {
  assert.deepEqual(queryTokens('2x AH havermout 500g'), ['ah', 'havermout']);
  assert.deepEqual(queryTokens('2x'), []);
  assert.deepEqual(queryTokens('7up'), ['7up']);
});

test('accents and case do not matter', () => {
  assert.equal(search(products, 'CREME FRAICHE')[0].barcode, '4');
});

test('AH finds Albert Heijn products', () => {
  assert.deepEqual(search(products, 'ah havermout').map((p) => p.barcode), ['1']);
});

test('exact name sorts first and a flagged record is not preferred', () => {
  assert.equal(search(products, 'havermout')[0].barcode, '1');
});

test('whole words win, part words are only a fallback', () => {
  assert.deepEqual(search(products, 'kaas').map((p) => p.barcode), ['3']);
  assert.deepEqual(search(products, 'kaa'), []);
});

test('different grades ask for a choice instead of inventing one score', () => {
  const result = evaluateLine(products, 'havermout');
  assert.equal(result.status, 'range');
  assert.equal(result.low, 'A');
  assert.equal(result.high, 'C');
  assert.equal(result.grade, undefined);
});

test('several products with the same grade count as that grade', () => {
  const result = evaluateLine(products, 'koffie');
  assert.equal(result.status, 'uniform');
  assert.equal(result.grade, 'A');
});

test('a clear majority of products with a name counts as that grade', () => {
  const list = prepare([
    ['1', 'Melk', 'A', '', 'B', 0], ['2', 'Melk', 'B', '', 'B', 0], ['3', 'Melk', 'C', '', 'B', 0],
    ['4', 'Melk', 'D', '', 'A', 0], ['5', 'Melk chocolade', 'E', '', 'E', 0], ['6', 'Melk chocolade', 'F', '', 'E', 0],
  ]);
  const result = evaluateLine(list, 'melk');
  assert.equal(result.status, 'mostly');
  assert.equal(result.grade, 'B');
  assert.equal(result.topCount, 3);
  assert.equal(result.total, 4);
  assert.equal(result.hits.length, 6);
});

test('a real spread stays a range', () => {
  const list = prepare([
    ['1', 'Muesli', 'A', '', 'A', 0], ['2', 'Muesli', 'B', '', 'C', 0], ['3', 'Muesli', 'C', '', 'D', 0],
  ]);
  const result = evaluateLine(list, 'muesli');
  assert.equal(result.status, 'range');
  assert.equal(result.grade, undefined);
});

test('a chosen product resolves the line', () => {
  const chosen = products[1];
  const result = evaluateLine(products, 'havermout', chosen);
  assert.equal(result.status, 'resolved');
  assert.equal(result.grade, 'C');
});

test('an online result without a score is not counted as scored', () => {
  const result = evaluateLine(products, 'iets', { name: 'Iets', grade: null });
  const summary = summarise([result]);
  assert.equal(summary.scored, 0);
  assert.equal(summary.unscored, 1);
});

test('summary counts each state', () => {
  const list = ['pindakaas', 'havermout', 'creme fraiche', 'onbekend product', '3x'];
  const summary = summarise(list.map((line) => evaluateLine(products, line)));
  assert.deepEqual(summary, { total: 4, scored: 2, low: 1, choose: 1, missing: 1, unscored: 0 });
});

test('the list is trimmed and capped', () => {
  assert.deepEqual(parseList(' a \n\n b\r\n'), ['a', 'b']);
  assert.equal(parseList(Array(80).fill('x').join('\n')).length, 50);
});
