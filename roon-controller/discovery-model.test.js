'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {list, item, mixes, picks} = require('./discovery-model');
const objects = new Map();
const graph = {getObject: id => objects.get(String(id))};
function object(id, fields) {const o = {oid: BigInt(id), fields}; objects.set(String(id), o); return {$ref: BigInt(id)};}
const artwork = object(2, {'Image::Url': 'broker:///image/example.__ROON_IMAGE_SIZE__.jpg', 'Image::ImageId': 123n});
const album = object(3, {'Album::Title': 'Example Album', 'Album::PerformedBy': '[[42|Example Artist]]', 'Album::AlbumId': 1234n, 'Album::Image': artwork, 'Album::Source': 1});
test('normalises metadata without turning private IDs into official browse keys', () => {
  const result = item(graph, album);
  assert.equal(result.artist, 'Example Artist'); assert.equal(result.id, '1234');
  assert.equal(result.artwork.id, '123'); assert.equal(result.item_key, undefined);
});
test('resolves only returned list membership, bounds order and rejects malformed refs', () => {
  assert.deepEqual(list(graph, {$items: [album, artwork]}, 1), [graph.getObject(3n)]);
  assert.equal(list(graph, {Items: Buffer.from([1, 3])})[0].oid, 3n);
  assert.throws(() => list(graph, {Items: Buffer.from([1])}));
  assert.throws(() => list(graph, {}, 21));
});
test('retains current Daily Picks seed/context and ignores empty groups', () => {
  const result = picks(graph, {$items: [{ObjectId: Buffer.from('abc'), Reason: 'recent', OneBoxType: 'album_recommended_for_you', SeedAlbum: album, Albums: {$items: [album]}}, {Albums: {$items: []}}]});
  assert.equal(result.length, 1); assert.equal(result[0].seed.title, 'Example Album'); assert.equal(result[0].reason, 'recent');
});
test('decodes inline mix descriptions, artwork and touchstones', () => {
  const mix = object(4, {MixId: Buffer.from('mix'), PerformerMixDescription: {PerformerName: 'Example Artist', Avatar: artwork, Touchstones: {$items: ['Artist One', 'Artist Two']}}});
  const result = mixes(graph, {$items: [mix]});
  assert.equal(result[0].title, 'Example Artist Mix'); assert.deepEqual(result[0].context, ['Artist One', 'Artist Two']); assert.equal(result[0].artwork.id, '123');
});
test('missing metadata and unsafe artwork fail closed', () => {
  assert.equal(item(graph, {$ref: 999n}), null);
  const result = item(graph, {Title: 'Safe', Image: {Url: 'file:///etc/passwd'}});
  assert.equal(result.artwork.url, null);
});
