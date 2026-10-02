'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {BrowseManager, browserLayout, formatDuration, libraryItems, publicItem, rootItems, safeSession, withFallbackImage} = require('./browse-state');

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

test('browser home keeps the four visual destinations in a deliberate order', () => {
  const items = ['My Live Radio', 'TIDAL', 'Genres', 'Library', 'Playlists'].map(title => ({title, item_key: title}));
  assert.deepEqual(rootItems(items).map(item => item.title), ['Library', 'Playlists', 'Genres', 'TIDAL']);
  assert.equal(browserLayout('browse', 0, {title: 'Explore'}, items).layout, 'home');
});

test('albums are readable lists while image-heavy artist lists retain labelled covers', () => {
  const items = [{title: 'One', image_key: '1'}, {title: 'Two', image_key: '2'}];
  assert.deepEqual(browserLayout('browse', 2, {title: 'Albums'}, items), {layout: 'list', show_labels: true});
  assert.deepEqual(browserLayout('browse', 2, {title: 'Artists'}, items), {layout: 'covers', show_labels: true});
});

test('album contents with a play action use track rows and preserve supplied durations', () => {
  const items = [{title: 'Play Album', hint: 'action'}, {title: 'Track', image_key: 'cover'}];
  assert.equal(browserLayout('browse', 3, {title: 'An Album'}, items).layout, 'list');
  assert.equal(publicItem({title: 'Track', duration: 245}).duration, '4:05');
  assert.equal(publicItem({title: 'Track', length: '3:09'}).duration, '3:09');
  assert.equal(formatDuration(null), '');
});

test('library is reduced to four useful destinations', () => {
  const list = {title: 'Library'};
  const items = ['Search', 'Artists', 'Albums', 'Tracks', 'Composers', 'Tags'].map(title => ({title, item_key: title}));
  assert.deepEqual(libraryItems(list, items).map(item => item.title), ['Artists', 'Albums', 'Tracks', 'Composers']);
  assert.equal(browserLayout('browse', 1, list, libraryItems(list, items)).layout, 'menu');
});

test('playlist collections and playlist tracks stay in list layouts', () => {
  const pictured = [{title: 'One', image_key: '1'}, {title: 'Two', image_key: '2'}];
  assert.equal(browserLayout('browse', 1, {title: 'Playlists'}, pictured).layout, 'list');
  assert.equal(browserLayout('browse', 2, {title: 'Evening vibes', subtitle: '437 Tracks'}, pictured).layout, 'list');
});

test('album artwork fills child track rows when Roon omits redundant image keys', () => {
  const items = withFallbackImage([
    {title: 'Play Album', hint: 'action'},
    {title: 'Track One', image_key: null},
    {title: 'Track Two', image_key: 'specific'}
  ], 'album-cover');
  assert.equal(items[0].image_key, undefined);
  assert.equal(items[1].image_key, 'album-cover');
  assert.equal(items[2].image_key, 'specific');
});

test('A-Z jump loads the page containing the requested album initial', async () => {
  const titles = [...Array(20)].map((_, index) => `Album ${index + 1}`)
    .concat([...Array(20)].map((_, index) => `Blue ${index + 1}`))
    .concat([...Array(20)].map((_, index) => `Coltrane ${index + 1}`));
  const service = {
    load(options, callback) {
      const items = titles.slice(options.offset, options.offset + options.count).map((title, index) => ({title, item_key: String(options.offset + index)}));
      callback(false, {offset: options.offset, list: {level: 2, title: 'Albums', count: titles.length}, items});
    }
  };
  const manager = new BrowseManager(() => service, () => ({zone_id: 'zone'}));
  manager.sessions.set('pihome-touch', {status: 'ready', hierarchy: 'browse', level: 2, title: 'Albums', count: titles.length, offset: 0, items: [], az_index: true, has_more: true});
  const result = await manager.run('touch', 'jump', {letter: 'C'});
  assert.equal(result.items[0].title.startsWith('C'), true);
  assert.equal(result.offset, 40);
});
