'use strict';

function playingMetadata(zone) {
  const playing = zone?.now_playing || {};
  const lines = playing.three_line || playing.two_line || playing.one_line || {};
  return {
    track: lines.line1 || '', artist: lines.line2 || '', album: lines.line3 || '',
    image_key: playing.image_key || null,
    key: [lines.line2, lines.line3].map(value => String(value || '').trim().toLowerCase()).join('|')
  };
}

const clean = value => String(value || '').trim().toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ');

function chooseItem(items, title) {
  const wanted = clean(title);
  if (!wanted) return null;
  return (items || []).filter(item => item?.item_key && item.hint !== 'header')
    .map(item => ({item, score: clean(item.title) === wanted ? 3 : clean(item.title).includes(wanted) || wanted.includes(clean(item.title)) ? 2 : 0}))
    .filter(candidate => candidate.score > 0).sort((a, b) => b.score - a.score)[0]?.item || null;
}

const request = (service, method, options) => new Promise((resolve, reject) => {
  service[method](options, (error, result) => error ? reject(new Error(String(error))) : resolve(result || {}));
});

async function searchItem(service, zoneId, query, category, title, session) {
  await request(service, 'browse', {hierarchy: 'search', pop_all: true, multi_session_key: session, zone_or_output_id: zoneId});
  let loaded = await request(service, 'load', {hierarchy: 'search', multi_session_key: session, offset: 0, count: 20});
  const prompt = (loaded.items || []).find(candidate => candidate.input_prompt && candidate.item_key);
  if (!prompt) return null;
  await request(service, 'browse', {hierarchy: 'search', item_key: prompt.item_key, input: query, multi_session_key: session, zone_or_output_id: zoneId});
  loaded = await request(service, 'load', {hierarchy: 'search', multi_session_key: session, offset: 0, count: 60});
  let item = chooseItem(loaded.items, title);
  if (item && clean(item.title) === clean(title)) return item;
  const group = chooseItem(loaded.items, category);
  if (!group) return null;
  await request(service, 'browse', {hierarchy: 'search', item_key: group.item_key, multi_session_key: session, zone_or_output_id: zoneId});
  loaded = await request(service, 'load', {hierarchy: 'search', multi_session_key: session, offset: 0, count: 60});
  return chooseItem(loaded.items, title);
}

async function albumTracks(service, zoneId, item, session) {
  if (!item?.item_key) return [];
  await request(service, 'browse', {hierarchy: 'search', item_key: item.item_key, multi_session_key: session, zone_or_output_id: zoneId});
  const loaded = await request(service, 'load', {hierarchy: 'search', multi_session_key: session, offset: 0, count: 40});
  return (loaded.items || []).filter(candidate => candidate.hint !== 'header' && candidate.title && candidate.hint !== 'action')
    .slice(0, 30).map(candidate => ({title: candidate.title, subtitle: candidate.subtitle || ''}));
}

async function loadDetails(service, zone) {
  const metadata = playingMetadata(zone);
  const base = {status: 'ready', ...metadata, album_image_key: metadata.image_key, artist_image_key: null, subtitle: '', tracks: []};
  if (!service || (!metadata.album && !metadata.artist)) return base;
  const stamp = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const [album, artist] = await Promise.all([
    metadata.album ? searchItem(service, zone.zone_id, [metadata.album, metadata.artist].filter(Boolean).join(' '), 'Albums', metadata.album, `${stamp}-album`) : null,
    metadata.artist ? searchItem(service, zone.zone_id, metadata.artist, 'Artists', metadata.artist, `${stamp}-artist`) : null
  ]);
  base.album_image_key = album?.image_key || metadata.image_key;
  base.artist_image_key = artist?.image_key || null;
  base.subtitle = album?.subtitle || artist?.subtitle || '';
  try { base.tracks = await albumTracks(service, zone.zone_id, album, `${stamp}-album`); } catch (_) {}
  return base;
}

module.exports = {playingMetadata, chooseItem, loadDetails};
