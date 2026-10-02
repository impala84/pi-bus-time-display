const $ = id => document.getElementById(id);
let state = null;
let lastTick = Date.now();
let musicView = 'now';
let queueSignature = '';
let inputSignature = '';
let lastActiveInput = '';
let browserState = null;
let browserLoading = false;
let browserRendering = false;
let browserScrollRestore = null;
const browserSession = sessionStorage.getItem('pi-home-roon-browser') || (globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`);
sessionStorage.setItem('pi-home-roon-browser', browserSession);
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

const scrollingCopy = new Map();

function setScrollingText(element, text) {
  const value = String(text || '');
  let entry = scrollingCopy.get(element);
  if (!entry) {
    const content = document.createElement('span'); content.className = 'scrolling-content';
    element.replaceChildren(content); entry = {content, animation: null, value: ''}; scrollingCopy.set(element, entry);
  }
  if (entry.value === value) return;
  entry.value = value; entry.content.textContent = value;
  requestAnimationFrame(() => refreshScrollingText(element));
}

function refreshScrollingText(element) {
  const entry = scrollingCopy.get(element);
  if (!entry) return;
  if (entry.animation) { entry.animation.cancel(); entry.animation = null; }
  const distance = Math.ceil(entry.content.scrollWidth - element.clientWidth);
  element.classList.toggle('is-scrolling', distance > 4);
  if (distance <= 4 || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const startPause = 10000; const endPause = 5000;
  const outward = Math.max(4500, distance / 22 * 1000); const returning = Math.max(3000, distance / 34 * 1000);
  const total = startPause + outward + endPause + returning;
  entry.animation = entry.content.animate([
    {transform: 'translateX(0)', offset: 0},
    {transform: 'translateX(0)', offset: startPause / total},
    {transform: `translateX(${-distance}px)`, offset: (startPause + outward) / total},
    {transform: `translateX(${-distance}px)`, offset: (startPause + outward + endPause) / total},
    {transform: 'translateX(0)', offset: 1}
  ], {duration: total, iterations: Infinity, easing: 'linear'});
}

let scrollingResizeTimer = null;
addEventListener('resize', () => {
  clearTimeout(scrollingResizeTimer);
  scrollingResizeTimer = setTimeout(() => scrollingCopy.forEach((_, element) => refreshScrollingText(element)), 150);
});

function compactLabel(label) {
  const words = String(label || '').trim().split(/\s+/).filter(Boolean);
  return (words[words.length - 1] || '').toUpperCase();
}

function setNavLabel(button, label) {
  const full = String(label || '').trim().toUpperCase();
  if (button.dataset.fullLabel === full) return;
  button.dataset.fullLabel = full;
  button.setAttribute('aria-label', label);
  button.replaceChildren();
  const wide = document.createElement('span'); wide.className = 'nav-label-full'; wide.textContent = full;
  const compact = document.createElement('span'); compact.className = 'nav-label-compact'; compact.textContent = compactLabel(label);
  button.append(wide, compact);
}

async function post(path, data) {
  await fetch(api(path), {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
}

function render(next) {
  state = next;
  const labels = next.labels || {};
  $('roon-link').textContent = labels.display || 'Roon';
  setNavLabel($('now-tab'), labels.now_playing || 'Now Playing');
  setNavLabel($('queue-tab'), labels.queue || 'Queue');
  setNavLabel($('browse-tab'), labels.browse || 'Browse');
  $('browse-tab').hidden = !next.browser_enabled;
  if (!next.browser_enabled && musicView === 'browse') musicView = 'now';
  lastTick = Date.now();
  const zone = next.zone;
  const amplifier = next.amplifier || {};
  const activeInput = String(amplifier.active_input?.id || '');
  if (activeInput !== lastActiveInput) {
    if (activeInput) musicView = 'source';
    else if (lastActiveInput && musicView === 'source') musicView = 'now';
    lastActiveInput = activeInput;
  }
  renderAmplifier(amplifier, zone);
  // Keep bounded secondary views current while an external input is visible,
  // so opening Queue or Details never waits for a later SSE update.
  renderQueue(next.queue || {});
  renderDetails(next.details || {});
  const external = Boolean(amplifier.connected && amplifier.active_input);
  const externalView = external && musicView === 'source';
  $('source-view').hidden = !externalView;
  $('now-view').hidden = musicView !== 'now';
  $('queue-view').hidden = musicView !== 'queue';
  $('browser-view').hidden = musicView !== 'browse';
  $('details-view').hidden = musicView !== 'details';
  $('now-tab').disabled = $('queue-tab').disabled = $('browse-tab').disabled = false;
  if (externalView) return;
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
  setScrollingText($('title'), lines.line1 || 'Nothing playing');
  setScrollingText($('artist'), [lines.line2, lines.line3].filter(Boolean).join(' · ') || 'Roon');
  if (playing.image_key) {
    const url = api(`/api/image?key=${encodeURIComponent(playing.image_key)}`);
    if ($('art').src !== location.origin + url) $('art').src = url;
    $('placeholder').hidden = true;
  } else {
    $('art').removeAttribute('src');
    $('placeholder').hidden = false;
  }

  $('play').innerHTML = external ? playIcon : (zone.state === 'playing' ? pauseIcon : playIcon);
  $('play').disabled = external ? !zone.can_play && !zone.can_pause : !(zone.can_play || zone.can_pause);
  $('previous').disabled = external || !zone.can_previous;
  $('next').disabled = external || !zone.can_next;
  const length = playing.length || 1;
  $('seek').max = length;
  $('seek').value = zone.seek_position || 0;
  $('elapsed').textContent = format(zone.seek_position);
  $('remaining').textContent = `−${format(length - (zone.seek_position || 0))}`;

  const volume = amplifier.connected && amplifier.volume ? {min: 0, max: 100, step: 1, value: amplifier.volume.value, is_muted: amplifier.volume.muted} : zone.output?.volume;
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

function renderAmplifier(amplifier, zone) {
  const inputs = amplifier.inputs || [];
  const signature = JSON.stringify([amplifier.connected, amplifier.active_input?.id, inputs.map(item => [item.id, item.name])]);
  if (signature !== inputSignature) {
    inputSignature = signature;
    const picker = $('music-nav'); picker.querySelectorAll('.source-input').forEach(button => button.remove());
    inputs.forEach(input => picker.insertBefore(inputButton(input, musicView === 'source' && String(input.id) === String(amplifier.active_input?.id)), $('now-tab')));
  }
  const active = amplifier.active_input;
  $('now-tab').classList.toggle('active', musicView === 'now'); $('queue-tab').classList.toggle('active', musicView === 'queue'); $('browse-tab').classList.toggle('active', musicView === 'browse');
  $('source-title').textContent = active?.name || 'External input';
  $('source-subtitle').textContent = [amplifier.player?.name || amplifier.player?.model, amplifier.playback?.format].filter(Boolean).join(' · ') || amplifier.status || 'BluOS amplifier';
  const volume = amplifier.volume;
  $('amp-volume-panel').hidden = !volume;
  if (volume) { $('amp-volume-value').textContent = Math.round(volume.value ?? 0); $('amp-mute').textContent = volume.muted ? 'UNMUTE' : 'MUTE'; }
}

function inputButton(input, active) {
  const button = document.createElement('button'); button.className = `source-input${active ? ' active' : ''}`; setNavLabel(button, input.name);
  button.dataset.inputId = input.id; button.onclick = () => { setMusicView('source'); post('/api/bluos/input', {input_id: input.id}); }; return button;
}

function queueRow(item) {
  const button = document.createElement('button');
  button.className = `queue-row${item.is_current ? ' current' : ''}${item.is_previous ? ' previous' : ''}`;
  if (!item.is_current) button.onclick = () => post('/api/queue/play', {queue_item_id: item.queue_item_id});
  const artwork = document.createElement('span'); artwork.className = `queue-art${item.is_current ? ' playing' : ''}`;
  if (item.image_key) {
    const image = document.createElement('img'); image.loading = 'lazy'; image.alt = ''; image.src = api(`/api/image?key=${encodeURIComponent(item.image_key)}&size=96`); artwork.append(image);
  }
  if (item.is_current) { const playing = document.createElement('span'); playing.className = 'queue-play-badge'; playing.textContent = '▶'; artwork.append(playing); }
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
  const browse = view === 'browse';
  const details = view === 'details';
  const source = view === 'source';
  $('now-view').hidden = queue || browse || details || source; $('queue-view').hidden = !queue; $('browser-view').hidden = !browse; $('details-view').hidden = !details; $('source-view').hidden = !source;
  $('now-tab').classList.toggle('active', view === 'now'); $('queue-tab').classList.toggle('active', queue); $('browse-tab').classList.toggle('active', browse);
  document.querySelectorAll('.source-input').forEach(button => button.classList.toggle('active', source && String(button.dataset.inputId) === String(state?.amplifier?.active_input?.id)));
  if (queue) requestAnimationFrame(scrollQueueToCurrent);
  if (browse && !browserState) browseCommand('section', {section: 'albums'});
}

function browserRow(item) {
  if (item.hint === 'header') {
    const heading = document.createElement('h3'); heading.className = 'browser-section'; heading.textContent = item.title; return heading;
  }
  const button = document.createElement('button'); button.className = `browser-row${item.action ? ' action' : ''}`; button.disabled = !item.item_key;
  const artwork = document.createElement('span'); artwork.className = `browser-art${item.action ? ' action-icon' : ''}`;
  if (item.action) artwork.append(browserActionIcon(item.title));
  else if (item.image_key) { const image = document.createElement('img'); image.loading = 'lazy'; image.alt = ''; image.src = api(`/api/image?key=${encodeURIComponent(item.image_key)}&size=128`); artwork.append(image); }
  const copy = document.createElement('span'); copy.className = 'browser-copy'; const title = document.createElement('strong'); title.textContent = item.title || 'Untitled'; copy.append(title);
  if (item.subtitle) { const subtitle = document.createElement('small'); subtitle.textContent = item.subtitle; copy.append(subtitle); }
  const arrow = document.createElement('span'); arrow.className = 'browser-arrow'; arrow.textContent = item.duration || '';
  button.append(artwork, copy, arrow); button.onclick = () => browseCommand('open', {item_key: item.item_key}); return button;
}

function browserActionIcon(title) {
  const value = String(title || '').toLowerCase();
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('aria-hidden', 'true');
  if (/add next/.test(value)) svg.innerHTML = '<path d="M4 6h10M4 12h7M4 18h10M18 9v6M15 12h6"/>';
  else if (/queue/.test(value)) svg.innerHTML = '<path d="M5 6h14M5 12h14M5 18h9"/><path d="m17 16 3 2-3 2z"/>';
  else if (/shuffle/.test(value)) svg.innerHTML = '<path d="M4 7h3c5 0 5 10 10 10h3M17 4l3 3-3 3M4 17h3c2 0 3.3-1.5 4.4-3.3M17 14l3 3-3 3"/>';
  else if (/from here/.test(value)) svg.innerHTML = '<path d="M5 5v14M9 6l10 6-10 6z"/>';
  else svg.innerHTML = '<path d="m8 5 11 7-11 7z"/>';
  return svg;
}

function browserTileSymbol(title, section) {
  const value = String(title || '').toLowerCase();
  if (section === 'playlists') return '≡';
  if (value.includes('jazz')) return '♪';
  if (value.includes('classical')) return '♬';
  if (value.includes('electronic')) return '⌁';
  if (value.includes('pop') || value.includes('rock')) return '⚡';
  if (value.includes('stage') || value.includes('screen') || value.includes('soundtrack')) return '★';
  if (value.includes('folk') || value.includes('country')) return '♧';
  if (value.includes('blues')) return '♭';
  if (value.includes('rap') || value.includes('hip-hop') || value.includes('r&b')) return '♫';
  if (value.includes('reggae')) return '≋';
  if (value.includes('latin') || value.includes('world') || value.includes('international')) return '◈';
  if (value.includes('vocal') || value.includes('easy listening')) return '♩';
  if (value.includes('new age') || value.includes('ambient')) return '✦';
  if (value.includes('holiday')) return '❄';
  if (value.includes('children')) return '☺';
  if (value.includes('religious') || value.includes('gospel')) return '✦';
  return String(title || '?').trim().charAt(0).toUpperCase() || '?';
}

function browserCard(item, layout, showLabels, section, showSubtitles = true) {
  const button = document.createElement('button'); button.className = `browser-card ${layout}`; button.disabled = !item.item_key;
  if (layout === 'covers' || layout === 'tiles') {
    const artwork = document.createElement('span'); artwork.className = 'browser-card-art';
    if (item.image_key) { const image = document.createElement('img'); image.loading = 'lazy'; image.alt = ''; image.src = api(`/api/image?key=${encodeURIComponent(item.image_key)}&size=320`); artwork.append(image); }
    else if (layout === 'tiles') { const icon = document.createElement('span'); icon.className = 'browser-tile-icon'; icon.textContent = browserTileSymbol(item.title, section); artwork.append(icon); }
    button.append(artwork);
  } else {
    const icon = document.createElement('span'); icon.className = 'browser-card-icon'; icon.setAttribute('aria-hidden', 'true'); icon.textContent = /playlist/i.test(item.title) ? '≡' : /genre/i.test(item.title) ? '◉' : /artist/i.test(item.title) ? '●' : /album|library/i.test(item.title) ? '▦' : '›'; button.append(icon);
  }
  if (layout !== 'covers' || showLabels) {
    const copy = document.createElement('span'); copy.className = 'browser-card-copy'; const title = document.createElement('strong'); title.textContent = item.title || 'Untitled'; copy.append(title);
    if (showLabels && showSubtitles && item.subtitle) { const subtitle = document.createElement('small'); subtitle.textContent = item.subtitle; copy.append(subtitle); }
    if (layout === 'tiles' && section === 'genres') button.querySelector('.browser-card-art').append(copy);
    else { if (layout === 'tiles') button.classList.add('playlist-card'); button.append(copy); }
  }
  button.setAttribute('aria-label', [item.title, item.subtitle].filter(Boolean).join(', ')); button.onclick = () => browseCommand('open', {item_key: item.item_key}); return button;
}

function renderBrowser(data) {
  browserRendering = true; browserState = data; browserLoading = false;
  $('browser-back').hidden = !data.can_back; $('browser-back').disabled = !data.can_back; $('browser-loading-more').hidden = true;
  document.querySelectorAll('[data-browser-section]').forEach(button => button.classList.toggle('active', button.dataset.browserSection === (data.section || 'albums')));
  $('browser-scrubber').hidden = !data.alpha_scrub;
  $('browser-message').hidden = !data.message; $('browser-message').textContent = data.message || ''; $('browser-message').classList.toggle('error', Boolean(data.error));
  const list = $('browser-list'); list.replaceChildren(); list.className = `browser-list layout-${data.layout || 'list'}`;
  if (data.status === 'unavailable') { const empty = document.createElement('p'); empty.className = 'queue-empty'; empty.textContent = 'Roon Browse is unavailable.'; list.append(empty); browserRendering = false; return; }
  (data.items || []).forEach(item => list.append(item.action ? browserRow(item) : (['home', 'menu', 'covers', 'tiles'].includes(data.layout) ? browserCard(item, data.layout, Boolean(data.show_labels), data.section, data.show_subtitles !== false) : browserRow(item))));
  if (!(data.items || []).length) { const empty = document.createElement('p'); empty.className = 'queue-empty'; empty.textContent = 'Nothing is available here.'; list.append(empty); }
  browserRendering = false;
  requestAnimationFrame(() => {
    if (browserScrollRestore !== null) { $('browser-scroll').scrollTop = browserScrollRestore; browserScrollRestore = null; }
    syncWebScrubber();
    maybeLoadMore();
  });
}

function positionWebScrubber(value) {
  const bounded = Math.max(0, Math.min(25, Math.round(value))); const letter = String.fromCharCode(65 + bounded);
  $('browser-scrub-letter').textContent = letter; $('browser-scrub-range').value = String(bounded); $('browser-scrubber').style.setProperty('--scrub-position', `${bounded / 25 * 100}%`);
}

function syncWebScrubber() {
  if (!browserState?.alpha_scrub || $('browser-scrubber').hidden) return;
  const top = $('browser-scroll').getBoundingClientRect().top + 45;
  const cards = [...$('browser-list').querySelectorAll('.browser-card')];
  const card = cards.find(candidate => candidate.getBoundingClientRect().bottom > top) || cards.at(-1);
  const first = String(card?.getAttribute('aria-label') || 'A').trim().replace(/^[^A-Za-z]+/, '').charAt(0).toUpperCase();
  positionWebScrubber(first >= 'A' && first <= 'Z' ? first.charCodeAt(0) - 65 : 0);
}

function maybeLoadMore() {
  const view = $('browser-scroll');
  if (musicView !== 'browse' || browserRendering || browserLoading || !browserState?.has_more) return;
  if (view.scrollHeight - view.scrollTop - view.clientHeight < 260) browseCommand('more');
}

async function browseCommand(action, data = {}) {
  if (browserLoading) return;
  browserLoading = true;
  if (action === 'more') { browserScrollRestore = $('browser-scroll').scrollTop; }
  else if (action === 'jump' || action === 'section') browserScrollRestore = 0;
  try {
    const options = action === 'current' ? {method: 'GET', cache: 'no-store'} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({session: browserSession, action, ...data})};
    const url = action === 'current' ? api(`/api/browse?session=${encodeURIComponent(browserSession)}`) : api('/api/browse');
    const response = await fetch(url, options); const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Browse failed'); renderBrowser(result);
  } catch (error) { browserLoading = false; renderBrowser({...(browserState || {}), status: 'ready', title: browserState?.title || 'Browse', items: browserState?.items || [], message: error.message, error: true}); }
}

function renderDetails(info) {
  const zone = state?.zone;
  const fallback = zone?.now_playing?.three_line || zone?.now_playing?.two_line || zone?.now_playing?.one_line || {};
  $('details-title').textContent = info.album || fallback.line3 || fallback.line1 || 'Nothing playing';
  $('details-artist').textContent = info.artist || fallback.line2 || '';
  $('details-subtitle').textContent = info.status === 'loading' ? 'Loading available Roon information…' : (info.subtitle || '');
  const metadata = info.metadata || {}; const facts = $('details-facts'); facts.replaceChildren();
  $('details-writeup').textContent = metadata.writeup || '';
  $('details-source').textContent = metadata.writeup_source ? `Source · ${metadata.writeup_source}` : '';
  const addFact = (name, value) => {
    if (!value) return;
    const item = document.createElement('div'); const term = document.createElement('dt'); const description = document.createElement('dd');
    term.textContent = name; description.textContent = value; item.append(term, description); facts.append(item);
  };
  addFact('Released', metadata.release_date || metadata.year);
  addFact('Genre', (metadata.genres || []).join(' · '));
  addFact('Type', metadata.type);
  addFact('Label', metadata.label);
  addFact('Format', metadata.format);
  addFact('Tracks', metadata.track_count ? String(metadata.track_count) : '');
  addFact('Country', metadata.country);
  addFact('Editions', metadata.edition_count > 1 ? String(metadata.edition_count) : '');
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
$('play').onclick = () => post('/api/control', {action: state?.amplifier?.active_input ? 'resume' : 'playpause'});
$('next').onclick = () => post('/api/control', {action: 'next'});
$('seek').onchange = event => post('/api/seek', {seconds: Number(event.target.value)});
$('volume').onchange = event => state.amplifier?.connected ? post('/api/bluos/volume', {value: Number(event.target.value)}) : post('/api/volume', {output_id: state.zone.output.id, value: Number(event.target.value)});
$('mute').onclick = () => state.amplifier?.connected ? post('/api/bluos/mute', {}) : post('/api/mute', {output_id: state.zone.output.id});
$('amp-down').onclick = () => post('/api/bluos/volume', {value: Number(state?.amplifier?.volume?.value || 0) - 2});
$('amp-up').onclick = () => post('/api/bluos/volume', {value: Number(state?.amplifier?.volume?.value || 0) + 2});
$('amp-mute').onclick = () => post('/api/bluos/mute', {});
$('now-tab').onclick = () => setMusicView('now');
$('queue-tab').onclick = () => setMusicView('queue');
$('browse-tab').onclick = () => setMusicView('browse');
$('browser-back').onclick = () => browseCommand('back');
document.querySelectorAll('[data-browser-section]').forEach(button => button.onclick = () => browseCommand('section', {section: button.dataset.browserSection}));
$('browser-scroll').addEventListener('scroll', () => { maybeLoadMore(); syncWebScrubber(); }, {passive: true});
$('browser-scrub-range').oninput = event => positionWebScrubber(Number(event.target.value));
$('browser-scrub-range').onchange = event => browseCommand('jump', {letter: String.fromCharCode(65 + Number(event.target.value))});
$('details-open').onclick = () => setMusicView('details');
$('details-artwork-close').onclick = () => setMusicView('now');
