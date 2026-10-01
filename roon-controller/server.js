'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const RoonApi = require('node-roon-api');
const RoonApiBrowse = require('node-roon-api-browse');
const RoonApiImage = require('node-roon-api-image');
const RoonApiStatus = require('node-roon-api-status');
const RoonApiTransport = require('node-roon-api-transport');
const {publicQueueItems, updateQueueState} = require('./queue-state');
const {playingMetadata, loadDetails} = require('./details-state');
const {BluOSClient, discoverPlayers} = require('./bluos-client');

const port = Number(process.env.PORT || 8766);
const staticDir = path.join(__dirname, 'static');
let core = null;
let transport = null;
let imageService = null;
let browseService = null;
let zones = new Map();
let queueItems = [];
let queueHistory = [];
let queueZoneId = null;
let queueSubscription = null;
let details = {status: 'unavailable'};
let detailsKey = '';
let detailsRequest = 0;
const detailsCache = new Map();
const listeners = new Set();
const imageCache = new Map();
const QUEUE_LIMIT = 100;
const IMAGE_CACHE_LIMIT = 64;
let runtimeConfig = null;
let runtimeConfigExpires = 0;

function configuredRuntime() {
  const now = Date.now();
  if (runtimeConfig && now < runtimeConfigExpires) return runtimeConfig;
  const defaults = {zoneName: process.env.ROON_ZONE_NAME || '', displayName: 'Roon', nowPlayingName: 'Now Playing', queueName: 'Queue', queueEnabled: true, bluos: {enabled: false, address: '', visibleInputs: [], inputNames: []}};
  try {
    const text = fs.readFileSync(process.env.CONFIG_PATH || '/etc/pi-bus-time-display/config.toml', 'utf8');
    const stringValue = name => JSON.parse(text.match(new RegExp(`^${name}\\s*=\\s*("(?:[^"\\\\]|\\\\.)*")`, 'm'))?.[1] || '""');
    const arrayValue = name => JSON.parse(text.match(new RegExp(`^${name}\\s*=\\s*(\\[[^\\n]*\\])`, 'm'))?.[1] || '[]');
    runtimeConfig = {
      zoneName: process.env.ROON_ZONE_NAME || stringValue('roon_zone_name'),
      displayName: stringValue('roon_display_name') || 'Roon',
      nowPlayingName: stringValue('roon_now_playing_name') || 'Now Playing',
      queueName: stringValue('roon_queue_name') || 'Queue',
      queueEnabled: text.match(/^roon_show_queue\s*=\s*(true|false)/m)?.[1] !== 'false',
      bluos: {
        enabled: text.match(/^bluos_enabled\s*=\s*(true|false)/m)?.[1] === 'true',
        address: stringValue('bluos_player_address'),
        visibleInputs: arrayValue('bluos_visible_inputs'),
        inputNames: arrayValue('bluos_input_names')
      }
    };
  } catch (_) { runtimeConfig = defaults; }
  runtimeConfigExpires = now + 1000;
  return runtimeConfig;
}

function configuredZoneName() {
  return configuredRuntime().zoneName;
}

function configuredQueueEnabled() {
  return configuredRuntime().queueEnabled;
}

function configuredBluOS() {
  return configuredRuntime().bluos;
}

function publicAmplifierState() {
  const state = bluos.publicState(); const config = configuredBluOS(); const visible = new Set(config.visibleInputs || []);
  const aliases = new Map((config.inputNames || []).map(item => { const split = String(item).indexOf('='); return split < 0 ? [item, ''] : [item.slice(0, split), item.slice(split + 1)]; }));
  const named = input => input ? {...input, name: aliases.get(String(input.id)) || input.name} : null;
  return {...state, inputs: (visible.size ? state.inputs.filter(input => visible.has(String(input.id))) : state.inputs).map(named), active_input: named(state.active_input)};
}

function selectedZone() {
  const requested = configuredZoneName();
  const all = [...zones.values()];
  return all.find(zone => zone.display_name === requested) ||
    all.find(zone => zone.state === 'playing') || all[0] || null;
}

function resumeRoon(zone) {
  const play = () => transport.control(zone, 'play', () => {});
  // BluOS can leave Roon reporting "playing" after a physical input takes over.
  // A deliberate pause/play edge makes the endpoint reclaim the audio source.
  if (zone.state === 'playing') transport.control(zone, 'pause', () => setTimeout(play, 160));
  else play();
}

function publicState() {
  bluos.refreshConfig().catch(() => {});
  const configured = configuredRuntime();
  const zone = selectedZone();
  const labels = {display: configured.displayName, now_playing: configured.nowPlayingName, queue: configured.queueName};
  if (!zone) return {connected: Boolean(core), authorised: Boolean(core), zones: [], zone: null, labels, queue: {status: 'unavailable', items: []}, details: {status: 'unavailable'}, amplifier: publicAmplifierState()};
  const output = (zone.outputs || []).find(item => item.volume) || (zone.outputs || [])[0] || null;
  return {
    connected: true,
    authorised: true,
    zones: [...zones.values()].map(item => ({id: item.zone_id, name: item.display_name})),
    zone: {
      id: zone.zone_id, name: zone.display_name, state: zone.state,
      now_playing: zone.now_playing || null,
      seek_position: zone.seek_position ?? zone.now_playing?.seek_position ?? 0,
      can_previous: Boolean(zone.is_previous_allowed), can_next: Boolean(zone.is_next_allowed),
      can_play: Boolean(zone.is_play_allowed), can_pause: Boolean(zone.is_pause_allowed),
      can_seek: Boolean(zone.is_seek_allowed), output: output ? {id: output.output_id, volume: output.volume || null} : null
    },
    queue: {status: !configuredQueueEnabled() ? 'disabled' : (queueZoneId === zone.zone_id ? 'ready' : 'loading'), items: queueZoneId === zone.zone_id ? publicQueueItems(queueItems, queueHistory) : []},
    labels, details, amplifier: publicAmplifierState()
  };
}

function broadcast() {
  const message = `data: ${JSON.stringify(publicState())}\n\n`;
  for (const response of listeners) response.write(message);
}

const bluos = new BluOSClient(configuredBluOS, () => broadcast());
bluos.refreshConfig().catch(() => {});

function mergeZones(command, data) {
  if (command === 'Subscribed') zones = new Map((data.zones || []).map(zone => [zone.zone_id, zone]));
  for (const zone of data.zones_added || []) zones.set(zone.zone_id, zone);
  for (const zone of data.zones_changed || []) zones.set(zone.zone_id, {...zones.get(zone.zone_id), ...zone});
  for (const zone of data.zones_removed || []) zones.delete(typeof zone === 'string' ? zone : zone.zone_id);
  ensureQueueSubscription();
  ensureDetails();
  broadcast();
}

function ensureDetails() {
  const zone = selectedZone();
  const metadata = playingMetadata(zone);
  const nextKey = zone ? `${zone.zone_id}|${metadata.key}` : '';
  if (!zone || !metadata.key) {
    detailsKey = nextKey; details = {status: 'unavailable', ...metadata}; return;
  }
  if (nextKey === detailsKey) return;
  detailsKey = nextKey;
  const cached = detailsCache.get(nextKey);
  if (cached) { details = cached; return; }
  details = {status: 'loading', ...metadata, album_image_key: metadata.image_key, artist_image_key: null, subtitle: '', tracks: []};
  const requestId = ++detailsRequest;
  loadDetails(browseService, zone).then(result => {
    if (requestId !== detailsRequest || detailsKey !== nextKey) return;
    details = result; detailsCache.set(nextKey, result);
    while (detailsCache.size > 24) detailsCache.delete(detailsCache.keys().next().value);
    broadcast();
  }).catch(() => {
    if (requestId !== detailsRequest || detailsKey !== nextKey) return;
    details = {...details, status: 'ready'}; broadcast();
  });
}

function stopQueueSubscription() {
  const subscription = queueSubscription;
  queueSubscription = null;
  queueZoneId = null;
  queueItems = [];
  queueHistory = [];
  if (subscription?.unsubscribe) {
    try { subscription.unsubscribe(() => {}); } catch (_) {}
  }
}

function ensureQueueSubscription() {
  const zone = selectedZone();
  if (!transport || !zone || !configuredQueueEnabled()) {
    if (queueSubscription) stopQueueSubscription();
    return;
  }
  if (queueSubscription && queueZoneId === zone.zone_id) return;
  stopQueueSubscription();
  const subscribedZoneId = zone.zone_id;
  queueZoneId = subscribedZoneId;
  queueSubscription = transport.subscribe_queue(zone, QUEUE_LIMIT, (command, data) => {
    if (queueZoneId !== subscribedZoneId) return;
    const next = updateQueueState(command, data, queueItems, queueHistory, QUEUE_LIMIT);
    queueItems = next.items; queueHistory = next.history;
    broadcast();
  });
}

function cachedImage(key, size, callback) {
  const cacheKey = `${key}:${size}`;
  const cached = imageCache.get(cacheKey);
  if (cached) {
    imageCache.delete(cacheKey); imageCache.set(cacheKey, cached);
    return callback(null, cached.type, cached.data);
  }
  imageService.get_image(key, {scale: 'fit', width: size, height: size}, (error, type, data) => {
    if (!error && data) {
      imageCache.set(cacheKey, {type: type || 'image/jpeg', data});
      while (imageCache.size > IMAGE_CACHE_LIMIT) imageCache.delete(imageCache.keys().next().value);
    }
    callback(error, type, data);
  });
}

const roon = new RoonApi({
  extension_id: 'com.impala84.pi-bus-time-display',
  display_name: 'Pi Home Roon Controller',
  display_version: '0.9.7',
  publisher: 'Pi Home',
  email: 'noreply@example.invalid',
  website: 'https://github.com/impala84/pi-home',
  core_paired: pairedCore => {
    core = pairedCore;
    transport = core.services.RoonApiTransport;
    imageService = core.services.RoonApiImage;
    browseService = core.services.RoonApiBrowse;
    status.set_status('Connected to Roon; touchscreen controller ready', false);
    transport.subscribe_zones(mergeZones);
    broadcast();
  },
  core_unpaired: () => {
    stopQueueSubscription();
    core = transport = imageService = browseService = null;
    details = {status: 'unavailable'}; detailsKey = ''; detailsRequest += 1;
    zones.clear();
    status.set_status('Waiting for Roon authorisation', false);
    broadcast();
  }
});
const status = new RoonApiStatus(roon);
roon.init_services({required_services: [RoonApiTransport, RoonApiImage, RoonApiBrowse], provided_services: [status]});
status.set_status('Waiting for Roon authorisation', false);
roon.start_discovery();

function json(response, statusCode, body) {
  const data = Buffer.from(JSON.stringify(body));
  response.writeHead(statusCode, {'Content-Type': 'application/json', 'Content-Length': data.length, 'Cache-Control': 'no-store'});
  response.end(data);
}

function body(request) {
  return new Promise((resolve, reject) => {
    let data = '';
    request.on('data', chunk => { data += chunk; if (data.length > 4096) reject(new Error('Request too large')); });
    request.on('end', () => { try { resolve(data ? JSON.parse(data) : {}); } catch (error) { reject(error); } });
  });
}

function serveStatic(request, response) {
  const names = {'/': 'index.html', '/app.js': 'app.js', '/style.css': 'style.css', '/refinements.css': 'refinements.css', '/favicon.svg': 'favicon.svg'};
  const name = names[new URL(request.url, 'http://localhost').pathname];
  if (!name) return false;
  const types = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml'};
  const data = fs.readFileSync(path.join(staticDir, name));
  response.writeHead(200, {'Content-Type': types[path.extname(name)], 'Content-Length': data.length, 'Cache-Control': 'no-cache'});
  response.end(data);
  return true;
}

http.createServer(async (request, response) => {
  try {
    const url = new URL(request.url, 'http://localhost');
    if (request.method === 'GET' && url.pathname === '/api/state') { ensureQueueSubscription(); return json(response, 200, publicState()); }
    if (request.method === 'GET' && url.pathname === '/api/bluos/players') return json(response, 200, {players: await discoverPlayers()});
    if (request.method === 'GET' && url.pathname === '/api/bluos/inputs') return json(response, 200, {connected: bluos.publicState().connected, inputs: bluos.publicState().inputs});
    if (request.method === 'GET' && url.pathname === '/api/events') {
      response.writeHead(200, {'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no', Connection: 'keep-alive'});
      listeners.add(response); response.write(`data: ${JSON.stringify(publicState())}\n\n`);
      request.on('close', () => listeners.delete(response)); return;
    }
    if (request.method === 'GET' && url.pathname === '/api/image') {
      if (!imageService || !url.searchParams.get('key')) return response.writeHead(404).end();
      const size = Math.max(48, Math.min(900, Number(url.searchParams.get('size')) || 900));
      return cachedImage(url.searchParams.get('key'), size, (error, type, data) => {
        if (error) return response.writeHead(404).end();
        response.writeHead(200, {'Content-Type': type || 'image/jpeg', 'Cache-Control': 'private, max-age=3600'}); response.end(data);
      });
    }
    if (request.method === 'POST' && url.pathname.startsWith('/api/')) {
      const data = await body(request); const zone = selectedZone();
      if (url.pathname === '/api/bluos/input') {
        await bluos.selectInput(data.input_id); return json(response, 200, {ok: true});
      }
      if (url.pathname === '/api/bluos/volume') { await bluos.setVolume(data.value); return json(response, 200, {ok: true}); }
      if (url.pathname === '/api/bluos/mute') { await bluos.toggleMute(); return json(response, 200, {ok: true}); }
      if (!transport || !zone) return json(response, 409, {error: 'Roon is not connected'});
      if (url.pathname === '/api/control' && data.action === 'resume') resumeRoon(zone);
      else if (url.pathname === '/api/control' && ['previous', 'playpause', 'next'].includes(data.action)) transport.control(zone, data.action);
      else if (url.pathname === '/api/queue/play') {
        const item = [...queueHistory, ...queueItems].find(candidate => String(candidate.queue_item_id) === String(data.queue_item_id));
        if (!item) return json(response, 409, {error: 'That queue item is no longer available'});
        transport.play_from_here(zone, item.queue_item_id, () => {});
      }
      else if (url.pathname === '/api/seek' && zone.is_seek_allowed) transport.seek(zone, 'absolute', Number(data.seconds));
      else {
        const output = (zone.outputs || []).find(item => item.output_id === data.output_id) || (zone.outputs || []).find(item => item.volume);
        if (!output?.volume) return json(response, 409, {error: 'This zone has fixed volume'});
        if (url.pathname === '/api/volume') transport.change_volume(output, 'absolute', Number(data.value));
        else if (url.pathname === '/api/mute') transport.mute(output, output.volume.is_muted ? 'unmute' : 'mute');
        else return json(response, 404, {error: 'Unknown command'});
      }
      return json(response, 200, {ok: true});
    }
    if (request.method === 'GET' && serveStatic(request, response)) return;
    json(response, 404, {error: 'Not found'});
  } catch (error) { json(response, 400, {error: error.message}); }
}).listen(port, '127.0.0.1');
