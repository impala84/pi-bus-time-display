const $ = id => document.getElementById(id);
let state = null;
let lastTick = Date.now();
let musicView = 'now';
let queueSignature = '';
const proxied = location.pathname.startsWith('/roon');
const api = path => `${proxied ? '/roon' : ''}${path}`;
const mainOrigin = proxied ? location.origin : `${location.protocol}//${location.hostname}:8765`;
$('settings-link').href = `${mainOrigin}/admin`;
$('bus-link').href = `${mainOrigin}/`;
$('home-link').href = `${mainOrigin}/home.html`;

const playIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z"/></svg>';
const pauseIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6v12M15 6v12"/></svg>';
const format = value => {
  value = Math.max(0, Math.round(value || 0));
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
};

async function post(path, data) {
  await fetch(api(path), {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
}

function render(next) {
  state = next;
  lastTick = Date.now();
  const zone = next.zone;
  renderQueue(next.queue || {});
  renderDetails(next.details || {});
  if (!zone) {
    $('title').textContent = next.connected ? 'Choose a Roon zone' : 'Waiting for Roon';
    $('artist').textContent = next.connected ? 'Start playback in a zone' : 'Enable Pi Home Roon Controller in Roon → Settings → Extensions';
    $('art').removeAttribute('src');
    $('previous').disabled = $('play').disabled = $('next').disabled = true;
    $('volume-panel').hidden = true;
    return;
  }

  const playing = zone.now_playing || {};
  const lines = playing.three_line || playing.two_line || playing.one_line || {};
  $('zone').textContent = zone.name;
  $('title').textContent = lines.line1 || 'Nothing playing';
  $('artist').textContent = [lines.line2, lines.line3].filter(Boolean).join(' · ') || 'Roon';
  if (playing.image_key) {
    const url = api(`/api/image?key=${encodeURIComponent(playing.image_key)}`);
    if ($('art').src !== location.origin + url) $('art').src = url;
    $('placeholder').hidden = true;
  } else {
    $('art').removeAttribute('src');
    $('placeholder').hidden = false;
  }

  $('play').innerHTML = zone.state === 'playing' ? pauseIcon : playIcon;
  $('play').disabled = !(zone.can_play || zone.can_pause);
  $('previous').disabled = !zone.can_previous;
  $('next').disabled = !zone.can_next;
  const length = playing.length || 1;
  $('seek').max = length;
  $('seek').value = zone.seek_position || 0;
  $('elapsed').textContent = format(zone.seek_position);
  $('remaining').textContent = `−${format(length - (zone.seek_position || 0))}`;

  const volume = zone.output?.volume;
  $('volume-panel').hidden = !volume;
  $('fixed').hidden = Boolean(volume);
  if (volume) {
    $('volume').min = volume.min ?? 0;
    $('volume').max = volume.max ?? 100;
    $('volume').step = volume.step ?? 1;
    $('volume').value = volume.value ?? 0;
    $('volume-value').textContent = volume.type === 'db' ? `${volume.value} dB` : Math.round(volume.value);
    $('mute').textContent = volume.is_muted ? 'UNMUTE' : 'MUTE';
  }
}

function queueRow(item) {
  const button = document.createElement('button');
  button.className = `queue-row${item.is_current ? ' current' : ''}${item.is_previous ? ' previous' : ''}`;
  if (!item.is_current) button.onclick = () => post('/api/queue/play', {queue_item_id: item.queue_item_id});
  const artwork = document.createElement('span'); artwork.className = 'queue-art';
  if (item.image_key) {
    const image = document.createElement('img'); image.loading = 'lazy'; image.alt = ''; image.src = api(`/api/image?key=${encodeURIComponent(item.image_key)}&size=96`); artwork.append(image);
  }
  const copy = document.createElement('span'); copy.className = 'queue-copy';
  const title = document.createElement('strong'); title.textContent = item.title || 'Untitled track'; copy.append(title);
  const meta = document.createElement('small'); meta.textContent = [item.artist, item.album].filter(Boolean).join(' · ') || 'Roon'; copy.append(meta);
  const duration = document.createElement('time'); duration.textContent = item.length ? format(item.length) : '';
  button.append(artwork, copy, duration);
  return button;
}

function renderQueue(queue) {
  const items = queue.items || [];
  const signature = JSON.stringify(items.map(item => [item.queue_item_id, item.is_current, item.is_previous]));
  if (signature === queueSignature) return;
  queueSignature = signature;
  const list = $('queue-list'); list.replaceChildren();
  if (!items.length) {
    const empty = document.createElement('p'); empty.className = 'queue-empty';
    empty.textContent = queue.status === 'loading' ? 'Queue is loading…' : queue.status === 'disabled' ? 'Queue is disabled in Settings' : 'Nothing is queued';
    list.append(empty); return;
  }
  items.forEach(item => list.append(queueRow(item)));
  if (musicView === 'queue') requestAnimationFrame(scrollQueueToCurrent);
}

function scrollQueueToCurrent() {
  const current = $('queue-list').querySelector('.current');
  if (current) current.scrollIntoView({block: 'start'});
}

function setMusicView(view) {
  musicView = view;
  const queue = view === 'queue';
  const details = view === 'details';
  $('now-view').hidden = queue || details; $('queue-view').hidden = !queue; $('details-view').hidden = !details;
  $('now-tab').classList.toggle('active', view === 'now'); $('queue-tab').classList.toggle('active', queue);
  if (queue) requestAnimationFrame(scrollQueueToCurrent);
}

function renderDetails(info) {
  const zone = state?.zone;
  const fallback = zone?.now_playing?.three_line || zone?.now_playing?.two_line || zone?.now_playing?.one_line || {};
  $('details-title').textContent = info.album || fallback.line3 || fallback.line1 || 'Nothing playing';
  $('details-artist').textContent = info.artist || fallback.line2 || '';
  $('details-subtitle').textContent = info.status === 'loading' ? 'Loading available Roon information…' : (info.subtitle || '');
  const key = info.artist_image_key || info.album_image_key || info.image_key;
  if (key) { $('details-art').src = api(`/api/image?key=${encodeURIComponent(key)}&size=700`); $('details-placeholder').hidden = true; }
  else { $('details-art').removeAttribute('src'); $('details-placeholder').hidden = false; }
  const list = $('details-tracks'); list.replaceChildren();
  (info.tracks || []).forEach((track, index) => {
    const item = document.createElement('li');
    const number = document.createElement('span'); number.textContent = index + 1;
    const copy = document.createElement('span'); const title = document.createElement('strong'); title.textContent = track.title;
    copy.append(title); if (track.subtitle) { const subtitle = document.createElement('small'); subtitle.textContent = track.subtitle; copy.append(subtitle); }
    item.append(number, copy); list.append(item);
  });
}

fetch(api('/api/state'), {cache: 'no-store'})
  .then(response => response.ok ? response.json() : Promise.reject(new Error('Roon state unavailable')))
  .then(render)
  .catch(() => {});
new EventSource(api('/api/events')).onmessage = event => render(JSON.parse(event.data));
setInterval(() => {
  if (!state?.zone || state.zone.state !== 'playing') return;
  const delta = (Date.now() - lastTick) / 1000;
  const position = (state.zone.seek_position || 0) + delta;
  const length = state.zone.now_playing?.length || 1;
  $('seek').value = Math.min(position, length);
  $('elapsed').textContent = format(position);
  $('remaining').textContent = `−${format(length - position)}`;
}, 1000);

$('previous').onclick = () => post('/api/control', {action: 'previous'});
$('play').onclick = () => post('/api/control', {action: 'playpause'});
$('next').onclick = () => post('/api/control', {action: 'next'});
$('seek').onchange = event => post('/api/seek', {seconds: Number(event.target.value)});
$('volume').onchange = event => post('/api/volume', {output_id: state.zone.output.id, value: Number(event.target.value)});
$('mute').onclick = () => post('/api/mute', {output_id: state.zone.output.id});
$('now-tab').onclick = () => setMusicView('now');
$('queue-tab').onclick = () => setMusicView('queue');
$('details-open').onclick = () => setMusicView('details');
$('details-close').onclick = () => setMusicView('now');
