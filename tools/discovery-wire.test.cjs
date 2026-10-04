const {test} = require('node:test');
const assert = require('node:assert/strict');
const {brokerWireId, referencePreview} = require('./discovery-wire.cjs');

test('SOOD UUID converts only the .NET Guid mixed-endian fields', () => {
  assert.equal(brokerWireId('01234567-89ab-cdef-0123-456789abcdef'), '67452301ab89efcd0123456789abcdef');
});
test('invalid UUIDs fail before any connection', () => {
  for (const value of ['', 'not-a-core', '0123456789abcdef0123456789abcdef']) assert.throws(() => brokerWireId(value));
});
test('reference previews preserve membership/order and bound visible results', () => {
  assert.deepEqual(referencePreview(Buffer.from([3, 2, 3, 4]), 2), [{$ref: 2n}, {$ref: 3n}]);
  assert.deepEqual(referencePreview(Buffer.from([0])), []);
});
test('reference previews reject truncation, trailing bytes and inline markers', () => {
  for (const bytes of [[], [1], [1, 128], [0, 2], [1, 1], [1, 0], [0x87, 0x69]]) assert.throws(() => referencePreview(Buffer.from(bytes)));
});
