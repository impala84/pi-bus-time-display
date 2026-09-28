const $ = id => document.getElementById(id);
let state = null;
let lastTick = Date.now();

const playIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 5 11 7-11 7z"/></svg>';
const pauseIcon = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6v12M15 6v12"/></svg>';
const format = value => {
  value = Math.max(0, Math.round(value || 0));
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`;
};

async function post(path, data) {
  await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
}

function render(next) {
  state = next;
  lastTick = Date.now();
  const zone = next.zone;
  if (!zone) {
    $('title').textContent = next.connected ? 'Choose a Roon zone' : 'Waiting for Roon';
    $('artist').textContent = next.connected ? 'Start playback in a zone' : 'Enable Pi Bus Roon Controller in Roon → Settings → Extensions';
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
    const url = `/api/image?key=${encodeURIComponent(playing.image_key)}`;
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

new EventSource('/api/events').onmessage = event => render(JSON.parse(event.data));
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
