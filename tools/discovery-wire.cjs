'use strict';

// SOOD UUID text is not the .NET Guid byte sequence used by the private wire
// handshake. Keep this conversion explicit, tested, and outside production.
function brokerWireId(uuid) {
  if (!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(uuid || '')) throw new Error('Invalid discovered Core UUID');
  const bytes = Buffer.from(uuid.replaceAll('-', ''), 'hex');
  bytes.subarray(0, 4).reverse();
  bytes.subarray(4, 6).reverse();
  bytes.subarray(6, 8).reverse();
  return bytes.toString('hex');
}

function referencePreview(buffer, limit = 5) {
  if (!Buffer.isBuffer(buffer) || !Number.isSafeInteger(limit) || limit < 0 || limit > 20) throw new Error('Invalid collection preview');
  let pos = 0;
  const integer = () => {
    let n = 0n;
    for (let i = 0; i < 10 && pos < buffer.length; i++) {
      const byte = buffer[pos++]; n = (n << 7n) | BigInt(byte & 127);
      if (!(byte & 128)) return n;
    }
    throw new Error('Truncated or oversized reference varint');
  };
  const count = Number(integer());
  if (!Number.isSafeInteger(count) || count < 0 || count > 1000) throw new Error('Invalid reference count');
  const values = [];
  for (let i = 0; i < count; i++) {
    const id = integer();
    if (id < 2n) throw new Error('Expected an object reference, not null/inline data');
    if (i < limit) values.push({$ref: id});
  }
  if (pos !== buffer.length) throw new Error('Unexpected collection bytes');
  return values;
}

module.exports = {brokerWireId, referencePreview};
