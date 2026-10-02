'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {playingMetadata, chooseItem, chooseMusicBrainzGroup, musicBrainzFacts, parseBandcampPage, loadAlbumWriteup, loadMusicBrainzMetadata, loadDetails} = require('./details-state');

test('playingMetadata reads three-line Roon metadata', () => {
  assert.deepEqual(playingMetadata({now_playing: {three_line: {line1: 'Track', line2: 'Artist', line3: 'Album'}, image_key: 'art'}}),
    {track: 'Track', artist: 'Artist', album: 'Album', image_key: 'art', key: 'artist|album'});
});

test('chooseItem prefers an exact title and ignores headers', () => {
  const result = chooseItem([{title: 'Albums', item_key: 'header', hint: 'header'}, {title: 'Blue Train Deluxe', item_key: 'a'}, {title: 'Blue Train', item_key: 'b'}], 'Blue Train');
  assert.equal(result.item_key, 'b');
});

test('loadDetails uses the Roon search prompt and merges cached external facts', async () => {
  const sessions = new Map();
  const service = {
    browse(options, callback) {
      const session = sessions.get(options.multi_session_key) || {stage: 'prompt'};
      if (options.input) session.stage = options.input === 'Artist' ? 'artist-results' : 'album-results';
      else if (options.item_key === 'album') session.stage = 'tracks';
      sessions.set(options.multi_session_key, session); callback(false, {action: 'list', list: {count: 1}});
    },
    load(options, callback) {
      const stage = sessions.get(options.multi_session_key)?.stage;
      const items = stage === 'prompt' ? [{title: 'Search', item_key: 'search', input_prompt: {prompt: 'Search'}}]
        : stage === 'artist-results' ? [{title: 'Artist', item_key: 'artist', image_key: 'artist-art'}]
        : stage === 'album-results' ? [{title: 'Album', item_key: 'album', image_key: 'album-art', subtitle: '1999'}]
        : [{title: 'Track one', subtitle: '3:12'}];
      callback(false, {items});
    }
  };
  const enrich = async () => ({year: '1999', release_date: '1999-04-01', genres: ['Electronic'], type: 'Album', country: 'US', label: 'Example', format: 'CD', edition_count: 2, track_count: 1, source: 'MusicBrainz', writeup: 'A concise album story.', writeup_source: 'Wikipedia'});
  const result = await loadDetails(service, {zone_id: 'zone', now_playing: {three_line: {line1: 'Track one', line2: 'Artist', line3: 'Album'}, image_key: 'current'}}, enrich);
  assert.equal(result.artist_image_key, 'artist-art'); assert.equal(result.album_image_key, 'album-art'); assert.equal(result.subtitle, '1999'); assert.equal(result.tracks[0].title, 'Track one');
  assert.equal(result.metadata.year, '1999'); assert.deepEqual(result.metadata.genres, ['Electronic']);
});

test('MusicBrainz matching requires the exact album and artist', () => {
  const groups = [
    {id: 'wrong', title: 'Chrysalis Deluxe', score: 100, 'artist-credit': [{name: 'Someone Else'}]},
    {id: 'right', title: 'Chrysalis', score: 100, 'artist-credit': [{name: 'Emancipator'}]}
  ];
  assert.equal(chooseMusicBrainzGroup(groups, 'Chrysalis', 'Emancipator').id, 'right');
  assert.equal(chooseMusicBrainzGroup(groups, 'Unknown', 'Emancipator'), null);
});

test('MusicBrainz facts expose useful compact album metadata', () => {
  const facts = musicBrainzFacts({
    'first-release-date': '2011-11-21', 'primary-type': 'Album', 'secondary-types': ['Remix'],
    genres: [{name: 'Downtempo', count: 9}, {name: 'Electronic', count: 4}],
    releases: [{status: 'Official', date: '2011-11-21', country: 'US'}, {status: 'Official', date: '2012', country: 'GB'}]
  }, 12);
  assert.deepEqual(facts, {release_date: '2011-11-21', year: '2011', genres: ['Downtempo', 'Electronic'], type: 'Album · Remix', country: 'United States', label: '', format: '', edition_count: 2, track_count: 12, source: 'MusicBrainz'});
});

test('MusicBrainz enrichment performs a search then a structured lookup', async () => {
  const paths = [];
  const fetchJson = async path => {
    paths.push(path);
    return paths.length === 1 ? {'release-groups': [{id: 'abc', title: 'Album', score: 100, 'artist-credit': [{name: 'Artist'}]}]}
      : {id: 'abc', title: 'Album', 'first-release-date': '2004', 'primary-type': 'Album', genres: [{name: 'Ambient', count: 3}], releases: []};
  };
  const facts = await loadMusicBrainzMetadata('Album', 'Artist', 8, fetchJson);
  assert.equal(paths.length, 2); assert.match(paths[0], /release-group/); assert.match(paths[1], /\/abc\?/);
  assert.equal(facts.year, '2004'); assert.equal(facts.track_count, 8);
});

test('Bandcamp parsing returns artist notes and a small tag set', () => {
  const page = '<div class="tralbumData tralbum-about">A story &amp; some <b>context</b>.</div><a class="tag">electronic</a><a class="tag">downtempo</a>';
  assert.deepEqual(parseBandcampPage(page), {writeup: 'A story & some context.', tags: ['electronic', 'downtempo']});
});

test('album writeup prefers a linked Wikipedia summary', async () => {
  const group = {relations: [{url: {resource: 'https://en.wikipedia.org/wiki/Example_album'}}]};
  const result = await loadAlbumWriteup(group, null, async () => JSON.stringify({type: 'standard', extract: 'The album story.'}));
  assert.deepEqual(result, {writeup: 'The album story.', source: 'Wikipedia', tags: []});
});
