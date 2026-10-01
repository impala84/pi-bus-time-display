'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {BluOSClient, normaliseAddress, parseInputs, parsePlayer, parseStatus, parseVolume} = require('./bluos-client');

test('normalises a player hostname onto the BluOS port', () => {
  assert.equal(normaliseAddress('nad-m33.local'), 'http://nad-m33.local:11000');
  assert.equal(normaliseAddress('http://10.0.0.8:11000'), 'http://10.0.0.8:11000');
});

test('parses BluOS player, status and volume responses', () => {
  assert.deepEqual(parsePlayer('<SyncStatus id="abc" name="Living Room" modelName="NAD M33" brand="NAD"/>'), {id: 'abc', name: 'Living Room', model: 'NAD M33', brand: 'NAD'});
  assert.deepEqual(parseVolume('<volume db="-35.0" mute="1">22</volume>'), {value: 22, muted: true, db: -35});
  const status = parseStatus('<status etag="17"><state>stream</state><service>Capture</service><title1>HDMI eARC</title1><title2>Television</title2><streamUrl>capture:arc-1</streamUrl><secs>12</secs><totlen>90</totlen></status>');
  assert.equal(status.etag, '17'); assert.equal(status.title, 'HDMI eARC'); assert.equal(status.stream_url, 'capture:arc-1'); assert.equal(status.duration, 90);
});

test('keeps only selectable capture inputs', () => {
  const inputs = parseInputs('<browse><item id="input1" inputType="arc"><text>HDMI eARC</text><url>capture:arc-1</url><service>Capture</service></item><item id="cloud"><text>Spotify</text><url>spotify:</url><service>Cloud</service></item></browse>');
  assert.deepEqual(inputs, [{id: 'input1', name: 'HDMI eARC', input_type: 'arc', url: 'capture:arc-1'}]);
});

test('parses compact RadioBrowse input items', () => {
  assert.deepEqual(parseInputs('<browse><item id="input2" inputType="analog" text="Record player" url="capture:analog-1"/></browse>'), [{id: 'input2', name: 'Record player', input_type: 'analog', url: 'capture:analog-1'}]);
});

test('connects for playback and volume when input browsing is unavailable', async () => {
  const client = new BluOSClient(() => ({enabled: true, address: 'nad.local'}), () => {});
  client.base = 'http://nad.local:11000';
  client.request = async path => {
    if (path === '/RadioBrowse?service=Capture') throw new Error('unsupported');
    if (path === '/SyncStatus') return '<SyncStatus id="abc" name="Living Room" modelName="NAD M33" brand="NAD"/>';
    if (path === '/Volume') return '<volume db="-35" mute="0">22</volume>';
    return '<status etag="17"><state>stream</state><title1>Roon</title1></status>';
  };
  client.poll = () => {};
  await client.connect(0);
  assert.equal(client.publicState().connected, true);
  assert.deepEqual(client.publicState().inputs, []);
  assert.equal(client.publicState().volume.value, 22);
});
