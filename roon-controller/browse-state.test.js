'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {BrowseManager, browserLayout, formatDuration, libraryItems, publicItem, rootItems, safeSession, withAlbumArtist, withFallbackImage} = require('./browse-state');

function fakeService() {
  const sessions = new Map();
  const levels = {
    '': [{title: 'Library', item_key: 'library'}, {title: 'Playlists', item_key: 'playlists'}, {title: 'Genres', item_key: 'genres'}],
    library: [{title: 'Albums', item_key: 'albums'}, {title: 'Artists', item_key: 'artists'}],
    albums: [{title: 'A Moon Shaped Pool', subtitle: 'Radiohead', image_key: 'moon', item_key: 'album-a'}, {title: 'Blue Train', subtitle: 'John Coltrane', image_key: 'blue', item_key: 'album-b'}, {title: 'Kind of Blue', subtitle: 'Miles Davis', image_key: 'kind', item_key: 'album-k'}, {title: 'Zooropa', subtitle: 'U2', image_key: 'zoo', item_key: 'album-z'}],
    artists: [{title: 'Björk', image_key: 'bjork', item_key: 'artist-b'}, {title: 'Miles Davis', image_key: 'miles', item_key: 'artist-m'}],
    genres: [{title: 'Jazz', item_key: 'genre-jazz'}],
    playlists: [{title: 'Evening', item_key: 'playlist-evening'}],
    'albums/album-a': [{title: 'Play Album', hint: 'action', item_key: 'play-a'}, {title: 'Burn the Witch', duration: 220, item_key: 'track-a1'}]
  };
  return {
    browse(options, callback) {
      const previous = sessions.get(options.multi_session_key) || {path: '', hierarchy: options.hierarchy};
      let path = options.pop_all ? '' : previous.path;
      if (options.pop_levels) path = path.split('/').slice(0, -options.pop_levels).join('/');
      if (options.item_key && options.hierarchy === 'browse') {
        if (['library', 'playlists', 'genres'].includes(options.item_key)) path = options.item_key;
        else if (['albums', 'artists'].includes(options.item_key)) path = options.item_key;
        else if (options.item_key.startsWith('album-')) path = `albums/${options.item_key}`;
      }
      if (options.input) path = 'results';
      const hierarchy = options.hierarchy; sessions.set(options.multi_session_key, {path, hierarchy});
      const items = hierarchy === 'search' ? [] : (levels[path] || []);
      const title = hierarchy === 'search' ? (path === 'results' ? 'Search results' : 'Search') : (path ? path.split('/').at(-1).replace(/^./, value => value.toUpperCase()) : 'Browse');
      callback(false, {action: 'list', list: {level: path ? path.split('/').length : 0, title, count: items.length}});
    },
    load(options, callback) {
      const current = sessions.get(options.multi_session_key) || {path: '', hierarchy: options.hierarchy};
      const items = current.hierarchy === 'search' && current.path !== 'results'
        ? [{title: 'Search', item_key: 'prompt', input_prompt: {prompt: 'Search Roon'}}]
        : current.hierarchy === 'search' ? [{title: 'Blue Train', subtitle: 'John Coltrane', image_key: 'blue'}]
        : (levels[current.path] || []);
      const title = current.hierarchy === 'search' ? (current.path === 'results' ? 'Search results' : 'Search') : (current.path ? current.path.split('/').at(-1).replace(/^./, value => value.toUpperCase()) : 'Browse');
      callback(false, {offset: options.offset, list: {level: current.path ? current.path.split('/').length : 0, title, count: items.length}, items: items.slice(options.offset, options.offset + options.count)});
    }
  };
}

test('browser opens the album section directly and returns to it from an album', async () => {
  const manager = new BrowseManager(() => fake, () => ({zone_id: 'zone'})); const fake = fakeService();
  const root = await manager.run('touch', 'root');
  assert.equal(root.title, 'Albums'); assert.equal(root.items[0].title, 'A Moon Shaped Pool'); assert.equal(root.can_back, false); assert.equal(root.alpha_scrub, true);
  const album = await manager.run('touch', 'open', {item_key: 'album-a'});
  assert.equal(album.title, 'Album-a'); assert.equal(album.items[0].action, true); assert.equal(album.can_back, true);
  const back = await manager.run('touch', 'back'); assert.equal(back.title, 'Albums'); assert.equal(back.can_back, false);
});

test('browser search uses Roon input prompt and keeps sessions separate', async () => {
  const fake = fakeService(); const manager = new BrowseManager(() => fake, () => ({zone_id: 'zone'}));
  const result = await manager.run('phone', 'search', {query: 'Blue'});
  assert.equal(result.title, 'Search results'); assert.equal(result.items[0].title, 'Blue Train');
  const searchRoot = await manager.run('phone', 'back'); assert.equal(searchRoot.title, 'Search');
  const browseRoot = await manager.run('phone', 'back'); assert.equal(browseRoot.title, 'Albums');
  const touch = await manager.run('touch', 'root'); assert.equal(touch.items[0].title, 'A Moon Shaped Pool');
  assert.notEqual(safeSession('phone!?'), safeSession('touch'));
});

test('browser root removes TIDAL and keeps the remaining destinations in order', () => {
  const items = ['My Live Radio', 'TIDAL', 'Genres', 'Library', 'Playlists'].map(title => ({title, item_key: title}));
  assert.deepEqual(rootItems(items).map(item => item.title), ['Library', 'Playlists', 'Genres']);
  assert.equal(browserLayout('browse', 0, {title: 'Explore'}, items).layout, 'home');
});

test('section rail switches directly and alphabet jumps replace the loaded page', async () => {
  const fake = fakeService(); const manager = new BrowseManager(() => fake, () => ({zone_id: 'zone'}));
  const artists = await manager.run('touch', 'section', {section: 'artists'});
  assert.equal(artists.section, 'artists'); assert.equal(artists.items[0].title, 'Björk'); assert.equal(artists.alpha_scrub, true);
  const albums = await manager.run('touch', 'section', {section: 'albums'});
  const jumped = await manager.run('touch', 'jump', {letter: 'K'});
  assert.equal(jumped.offset, 2); assert.equal(jumped.items[0].title, 'Kind of Blue'); assert.equal(albums.section_root, true);
});

test('album and artist collections retain artwork grids', () => {
  const items = [{title: 'One', image_key: '1'}, {title: 'Two', image_key: '2'}];
  assert.deepEqual(browserLayout('browse', 2, {title: 'Albums'}, items), {layout: 'covers', show_labels: false});
  assert.deepEqual(browserLayout('browse', 2, {title: 'Artists'}, items), {layout: 'covers', show_labels: true});
});

test('album contents with a play action use track rows and preserve supplied durations', () => {
  const items = [publicItem({title: 'Play Album', hint: 'action_list'}), {title: 'Track', image_key: 'cover'}];
  assert.equal(items[0].action, true);
  assert.equal(browserLayout('browse', 3, {title: 'An Album'}, items).layout, 'list');
  assert.equal(publicItem({title: 'Track', duration: 245}).duration, '4:05');
  assert.equal(publicItem({title: 'Track', length: '3:09'}).duration, '3:09');
  assert.equal(formatDuration(null), '');
});

test('album track rows use the album artist rather than a long credits list', () => {
  const items = withAlbumArtist([
    publicItem({title: 'Play Album', hint: 'action'}),
    publicItem({title: 'Track one', subtitle: 'Justice, Xavier de Rosnay, Gaspard Augé'}),
    publicItem({title: 'Track two', subtitle: 'Justice, Featured Singer'})
  ]);
  assert.equal(items[1].subtitle, 'Justice');
  assert.equal(items[2].subtitle, 'Justice');
});

test('library is reduced to four useful destinations', () => {
  const list = {title: 'Library'};
  const items = ['Search', 'Artists', 'Albums', 'Tracks', 'Composers', 'Tags'].map(title => ({title, item_key: title}));
  assert.deepEqual(libraryItems(list, items).map(item => item.title), ['Artists', 'Albums', 'Tracks', 'Composers']);
  assert.equal(browserLayout('browse', 1, list, libraryItems(list, items)).layout, 'menu');
});

test('genre and playlist collections use tiles while playlist tracks stay in rows', () => {
  const pictured = [{title: 'One', image_key: '1'}, {title: 'Two', image_key: '2'}];
  assert.deepEqual(browserLayout('browse', 1, {title: 'Genres'}, pictured), {layout: 'tiles', show_labels: true, show_subtitles: false});
  assert.deepEqual(browserLayout('browse', 1, {title: 'Playlists'}, pictured), {layout: 'tiles', show_labels: true, show_subtitles: false});
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
