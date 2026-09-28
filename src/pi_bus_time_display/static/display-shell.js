const screen = document.getElementById('screen');
let target = '';

async function switchIfNeeded() {
  try {
    const response = await fetch('/api/display-target', {cache: 'no-store'});
    const next = (await response.json()).target;
    if (next !== target) {
      target = next;
      screen.src = next;
    }
  } catch (_) {
    // Keep showing the current screen during a brief service restart.
  }
}

switchIfNeeded();
setInterval(switchIfNeeded, 1000);
