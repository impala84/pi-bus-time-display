'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const {queueItemsFromMessage, publicQueueItems} = require('./queue-state');

test('keeps a subscribed queue in order and exposes compact display fields', () => {
  const raw = [
    {queue_item_id: 10, three_line: {line1: 'One', line2: 'Artist', line3: 'Album'}, length: 181, image_key: 'a'},
    {queue_item_id: 11, two_line: {line1: 'Two', line2: 'Another artist'}}
  ];
  const queue = publicQueueItems(queueItemsFromMessage('Subscribed', {items: raw}));
  assert.equal(queue.length, 2);
  assert.deepEqual(queue[0], {queue_item_id: 10, title: 'One', artist: 'Artist', album: 'Album', length: 181, image_key: 'a', is_current: true});
  assert.equal(queue[1].is_current, false);
});

test('accepts incremental queue changes without disturbing order', () => {
  const initial = [{queue_item_id: 10}, {queue_item_id: 12}];
  const changed = queueItemsFromMessage('Changed', {
    items_added: [{index: 1, item: {queue_item_id: 11}}],
    items_changed: [{queue_item_id: 12, title: 'Updated'}]
  }, initial);
  assert.deepEqual(changed.map(item => item.queue_item_id), [10, 11, 12]);
  assert.equal(changed[2].title, 'Updated');
});

test('clears state on unsubscribe', () => {
  assert.deepEqual(queueItemsFromMessage('Unsubscribed', {}, [{queue_item_id: 1}]), []);
});
