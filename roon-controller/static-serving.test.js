'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const staticDir = path.join(__dirname, 'static');
// Exercise the production handler without starting Roon discovery or touching pairing state.
const source = fs.readFileSync(path.join(__dirname, 'server.js'), 'utf8');
const start = source.indexOf('function serveStatic(');
const end = source.indexOf('\nhttp.createServer', start);
const serveStatic = vm.runInNewContext(`${source.slice(start, end)}\nserveStatic`, {fs, path, staticDir, URL});
function request(url) {
  const response = {writeHead(status, headers) {this.status = status; this.headers = headers;}, end(data) {this.data = data;}};
  return {served: serveStatic({url}, response), ...response};
}
test('production serves every script and stylesheet referenced by the Roon page', () => {
  const html = fs.readFileSync(path.join(staticDir, 'index.html'), 'utf8');
  const assets = [...html.matchAll(/(?:src|href)="([^"#]+\.(?:js|css)(?:\?[^" ]*)?)"/g)].map(match => match[1]);
  assert.ok(assets.includes('discovery.js?v=1102'));
  for (const asset of assets) {
    const response = request('/' + asset);
    assert.equal(response.served, true, asset);
    assert.equal(response.status, 200, asset);
    assert.ok(response.data.length > 0, asset);
    assert.match(response.headers['Content-Type'], asset.includes('.js') ? /^text\/javascript/ : /^text\/css/);
  }
});
test('production serves dynamically loaded Discover CSS and refuses arbitrary paths', () => {
  const script = fs.readFileSync(path.join(staticDir, 'discovery.js'), 'utf8');
  const asset = script.match(/css\.href='([^']+)'/)[1];
  const response = request('/' + asset);
  assert.equal(response.status, 200);
  assert.match(response.data.toString(), /body\[data-theme="roon"\]/);
  assert.equal(request('/server.js').served, false);
  assert.equal(request('/../server.js').served, false);
});
