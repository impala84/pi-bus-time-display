'use strict';
const test = require('node:test'); const assert = require('node:assert/strict'); const {EventEmitter} = require('node:events');
const {DiscoveryManager} = require('./discovery-state');
const tick = () => new Promise(resolve => setImmediate(resolve));
test('worker failures are cached, concurrent polls coalesce and private work is memory-bounded', async () => {
  let count = 0, child;
  const manager = new DiscoveryManager({spawn: (_, args, options) => {count++; assert.deepEqual(options.execArgv, ['--max-old-space-size=128']); child = new EventEmitter(); child.send = () => {}; child.kill = () => {}; return child;}});
  manager.setTarget({host:'example',brokerId:'00'});
  assert.equal(manager.state('daily').status, 'loading'); manager.state('daily'); await tick(); assert.equal(count,1);
  child.emit('error', new Error('private data')); await tick(); assert.equal(manager.state('daily').status,'unavailable'); assert.equal(count,1);
  assert.doesNotMatch(JSON.stringify(manager.state('daily')), /private data/);
});
test('cached results expire, and unpairing discards in-flight personal data', async () => {
  let now=0, child; const manager = new DiscoveryManager({now:()=>now,spawn:()=>{child=new EventEmitter();child.send=()=>{};child.kill=()=>{};return child;}});
  manager.setTarget({host:'example'}); manager.state('recent'); await tick(); child.emit('message',{ok:true,data:{items:[{title:'Example'}]}}); await tick();
  assert.equal(manager.state('recent').status,'ready'); now=300001; assert.equal(manager.state('recent').refreshing,true); await tick();
  manager.setTarget(null); child.emit('message',{ok:true,data:{items:[{title:'Personal'}]}}); await tick();
  assert.equal(manager.cache.size,0); assert.equal(manager.state('recent').status,'unavailable');
});
test('worker deadline terminates a hung reader and leaves the controller responsive', async () => {
  let killed=false; const manager=new DiscoveryManager({timeoutMs:5,spawn:()=>{const child=new EventEmitter();child.send=()=>{};child.kill=()=>{killed=true};return child;}});
  manager.setTarget({host:'example'}); manager.state('daily'); await manager.tail;
  assert.equal(killed,true); assert.equal(manager.state('daily').status,'unavailable');
});
test('public data replaces private artwork URLs with bounded keys and validates image origins',()=>{
  const manager=new DiscoveryManager();manager.setTarget({host:'example',httpPort:9330});
  const publicData=manager.decorate({items:[{kind:'album',id:'123',title:'Title',artist:'Artist',object_ref:'internal',artwork:{url:'broker:///image/example.__ROON_IMAGE_SIZE__.jpg'}}]});
  assert.equal(publicData.items[0].object_ref,undefined);assert.equal(publicData.items[0].artwork,undefined);
  assert.equal(publicData.items[0].key.length,24);assert.equal(manager.imageUrl(publicData.items[0].artwork_key),'http://example:9330/image/example.256.jpg');
  manager.images.set('unsafe','https://example.com/private');assert.equal(manager.imageUrl('unsafe'),null);
  manager.images.set('invalid','https://[');assert.equal(manager.imageUrl('invalid'),null);
  assert.equal(manager.imageUrl('unregistered'),null);
});
