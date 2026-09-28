(() => {
  if (document.getElementById('pi-bus-settings-button')) return;
  const button = document.createElement('a');
  button.id = 'pi-bus-settings-button';
  button.href = 'http://127.0.0.1:8765/admin';
  button.textContent = 'SETTINGS';
  button.setAttribute('aria-label', 'Open Pi Bus settings');
  Object.assign(button.style, {
    position: 'fixed', top: '18px', right: '18px', zIndex: '2147483647',
    padding: '13px 18px', border: '1px solid rgba(255,255,255,.28)',
    borderRadius: '999px', background: 'rgba(10,17,15,.88)', color: '#fff',
    font: '800 12px system-ui,sans-serif', letterSpacing: '.12em',
    textDecoration: 'none', boxShadow: '0 4px 18px rgba(0,0,0,.3)'
  });
  document.documentElement.appendChild(button);
})();
