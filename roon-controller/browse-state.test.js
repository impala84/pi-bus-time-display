'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {BrowseManager, safeSession} = require('./browse-state');

function fakeService() {
  const sessions = new Map();
  return {
    browse(options, callback) {
      let level = options.pop_all ? 0 : (sessions.get(options.multi_session_key)?.level || 0);
      if (options.item_key === 'albums') level = 1;
      if (options.pop_levels) level = Math.max(0, level - options.pop_levels);
      if (options.input) level = 1;
      sessions.set(options.multi_session_key, {level, hierarchy: options.hierarchy});
      callback(false, {action: 'list', list: {level, title: options.hierarchy === 'search' ? 'Search results' : level ? 'Albums' : 'Browse', count: level ? 2 : 1}});
    },
    load(options, callback) {
      const current = sessions.get(options.multi_session_key) || {level: 0, hierarchy: options.hierarchy};
      const items = current.hierarchy === 'search' && current.level === 0
        ? [{title: 'Search', item_key: 'prompt', input_prompt: {prompt: 'Search Roon'}}]
        : current.hierarchy === 'search' ? [{title: 'Blue Train', subtitle: 'John Coltrane', image_key: 'blue'}]
        : current.level ? [{title: 'Kind of Blue', subtitle: 'Miles Davis', image_key: 'kind'}, {title: 'Blue Train', subtitle: 'John Coltrane', image_key: 'blue'}]
        : [{title: 'Albums', item_key: 'albums', hint: 'list'}];
      const title = current.hierarchy === 'search' ? (current.level ? 'Search results' : 'Search') : (current.level ? 'Albums' : 'Browse');
      callback(false, {list: {level: current.level, title, count: items.length}, items: items.slice(options.offset, options.offset + options.count)});
    }
  };
}

test('browser drills into and returns from a Roon hierarchy', async () => {
  const manager = new BrowseManager(() => fake, () => ({zone_id: 'zone'})); const fake = fakeService();
  const root = await manager.run('touch', 'root');
  assert.equal(root.title, 'Browse'); assert.equal(root.items[0].title, 'Albums'); assert.equal(root.can_back, false);
  const albums = await manager.run('touch', 'open', {item_key: 'albums'});
  assert.equal(albums.title, 'Albums'); assert.equal(albums.items[0].image_key, 'kind'); assert.equal(albums.can_back, true);
  const back = await manager.run('touch', 'back'); assert.equal(back.level, 0);
});

test('browser search uses Roon input prompt and keeps sessions separate', async () => {
  const fake = fakeService(); const manager = new BrowseManager(() => fake, () => ({zone_id: 'zone'}));
  const result = await manager.run('phone', 'search', {query: 'Blue'});
  assert.equal(result.title, 'Search results'); assert.equal(result.items[0].title, 'Blue Train');
  const searchRoot = await manager.run('phone', 'back'); assert.equal(searchRoot.title, 'Search');
  const browseRoot = await manager.run('phone', 'back'); assert.equal(browseRoot.title, 'Browse');
  const touch = await manager.run('touch', 'root'); assert.equal(touch.items[0].title, 'Albums');
  assert.notEqual(safeSession('phone!?'), safeSession('touch'));
});
