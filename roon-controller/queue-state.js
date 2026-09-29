'use strict';

function queueItemsFromMessage(command, message, previous = []) {
  const data = message || {};
  if (command === 'Unsubscribed') return [];
  if (Array.isArray(data.items)) return data.items;
  if (Array.isArray(data.queue_items)) return data.queue_items;
  if (command !== 'Changed') return previous;

  let items = [...previous];
  for (const removed of data.items_removed || []) {
    const id = typeof removed === 'object' ? removed.queue_item_id : removed;
    items = items.filter(item => item.queue_item_id !== id);
  }
  for (const changed of data.items_changed || []) {
    const index = items.findIndex(item => item.queue_item_id === changed.queue_item_id);
    if (index >= 0) items[index] = {...items[index], ...changed};
  }
  for (const added of data.items_added || []) {
    const item = added.item || added;
    const index = Number.isInteger(added.index) ? added.index : items.length;
    items.splice(Math.max(0, Math.min(index, items.length)), 0, item);
  }
  for (const change of data.changes || []) {
    const operation = change.operation || change.op;
    const index = Math.max(0, Number(change.index) || 0);
    if (operation === 'remove') items.splice(index, Number(change.count) || 1);
    if (operation === 'insert') items.splice(index, 0, ...(change.items || (change.item ? [change.item] : [])));
    if (operation === 'replace') items.splice(index, Number(change.count) || 1, ...(change.items || (change.item ? [change.item] : [])));
  }
  return items;
}

function publicQueueItems(items) {
  return (items || []).map((item, index) => {
    const lines = item.three_line || item.two_line || item.one_line || {};
    return {
      queue_item_id: item.queue_item_id,
      title: lines.line1 || item.title || 'Untitled track',
      artist: lines.line2 || item.artist || '',
      album: lines.line3 || item.album || '',
      length: Number(item.length) || null,
      image_key: item.image_key || null,
      is_current: index === 0
    };
  }).filter(item => item.queue_item_id !== undefined && item.queue_item_id !== null);
}

module.exports = {queueItemsFromMessage, publicQueueItems};
