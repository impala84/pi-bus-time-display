'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {playingMetadata, chooseItem, loadDetails} = require('./details-state');

test('playingMetadata reads three-line Roon metadata', () => {
  assert.deepEqual(playingMetadata({now_playing: {three_line: {line1: 'Track', line2: 'Artist', line3: 'Album'}, image_key: 'art'}}),
    {track: 'Track', artist: 'Artist', album: 'Album', image_key: 'art', key: 'artist|album'});
});

test('chooseItem prefers an exact title and ignores headers', () => {
  const result = chooseItem([{title: 'Albums', item_key: 'header', hint: 'header'}, {title: 'Blue Train Deluxe', item_key: 'a'}, {title: 'Blue Train', item_key: 'b'}], 'Blue Train');
  assert.equal(result.item_key, 'b');
});

test('loadDetails uses the Roon search prompt and returns lightweight metadata', async () => {
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
  const result = await loadDetails(service, {zone_id: 'zone', now_playing: {three_line: {line1: 'Track one', line2: 'Artist', line3: 'Album'}, image_key: 'current'}});
  assert.equal(result.artist_image_key, 'artist-art'); assert.equal(result.album_image_key, 'album-art'); assert.equal(result.subtitle, '1999'); assert.equal(result.tracks[0].title, 'Track one');
});
