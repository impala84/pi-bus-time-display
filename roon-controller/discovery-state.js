'use strict';
const {fork} = require('node:child_process');
const path = require('node:path');
const {createHash} = require('node:crypto');
class DiscoveryManager {
  constructor({spawn = fork, now = Date.now, timeoutMs = 20000} = {}) {
    this.spawn = spawn; this.now = now; this.timeoutMs = timeoutMs;
    this.target = null; this.cache = new Map(); this.pending = new Map(); this.tail = Promise.resolve(); this.child = null; this.images = new Map();
  }
  setTarget(target) {
    if (JSON.stringify(target) === JSON.stringify(this.target)) return;
    this.target = target; this.cache.clear(); this.images.clear(); this.pending.clear(); this.child?.kill();
  }
  state(section, id = '') {
    if (!['recent', 'daily', 'releases', 'mix'].includes(section)) throw new Error('Unknown Discover section');
    if (section === 'mix' && (!/^[a-f0-9]{2,160}$/i.test(id) || id.length % 2)) throw new Error('Invalid mix reference');
    if (!this.target) return {status: 'unavailable', message: 'Connect and authorise Roon to use Discover.', items: []};
    const key = `${section}:${id}`; const cached = this.cache.get(key);
    if ((!cached || cached.expires <= this.now()) && !this.pending.has(key) && this.pending.size < 4) {
      const target = this.target;
      const job = this.tail.catch(() => {}).then(() => target === this.target ? this.run(target, section, id) : null).then(data => {
        if (!data || target !== this.target) return;
        this.cache.set(key, {...this.decorate(data), expires: this.now() + (data.status === 'ready' ? 300000 : 60000)});
        while (this.cache.size > 24) this.cache.delete(this.cache.keys().next().value);
      }).finally(() => {if (this.pending.get(key) === job) this.pending.delete(key);});
      this.pending.set(key, job); this.tail = job;
    }
    if (cached) {const {expires, ...data} = cached; return {...data, refreshing: this.pending.has(key)};}
    return {status: 'loading', message: 'Loading your Roon recommendations…', items: []};
  }
  decorate(data) {
    const visit = value => {
      if (!value || typeof value !== 'object') return value;
      if (Array.isArray(value)) return value.map(visit);
      const result = Object.fromEntries(Object.entries(value).filter(([key]) => key !== 'artwork' && key !== 'object_ref').map(([key,v])=>[key, visit(v)]));
      if (value.kind && value.title) result.key = createHash('sha256').update(JSON.stringify([value.kind,value.id,value.title,value.artist,value.album,value.release_id])).digest('hex').slice(0,24);
      if (value.artwork?.url) {
        const key = createHash('sha256').update(value.artwork.url).digest('hex').slice(0,24);
        this.images.set(key,value.artwork.url); result.artwork_key=key;
        while(this.images.size>256) this.images.delete(this.images.keys().next().value);
      }
      return result;
    };
    return visit(data);
  }
  find(key) {
    for(const cached of this.cache.values()) {
      const items=[...(cached.items||[]),...(cached.groups||[]).flatMap(group=>group.items||[])];
      const match=items.find(item=>item.key===key); if(match)return match;
    }
    return null;
  }
  imageUrl(key) {
    const url=this.images.get(key); if(!url||!this.target)return null;
    if(/^broker:\/\/\/image\/[A-Za-z0-9_-]+\.__ROON_IMAGE_SIZE__\.jpg$/.test(url)) return `http://${this.target.host}:${this.target.httpPort||9330}/${url.slice('broker:///'.length).replace('__ROON_IMAGE_SIZE__','256')}`;
    try {const target=new URL(url); return target.protocol==='https:'&&target.hostname==='images.tidal.com'?url:null;} catch {return null;}
  }
  run(target, section, id) {
    return new Promise(resolve => {
      let child, timer, settled = false;
      const finish = result => {
        if (settled) return; settled = true; clearTimeout(timer);
        if (this.child === child) this.child = null;
        child?.kill(); resolve(result);
      };
      const unavailable = () => finish({status: 'unavailable', message: 'Discover could not reach Roon. Normal playback controls are unaffected.', items: []});
      try {
        child = this.spawn(path.join(__dirname, 'discovery-worker.js'), [], {execArgv: ['--max-old-space-size=128'], stdio: ['ignore', 'ignore', 'ignore', 'ipc'], env: {PATH: process.env.PATH}});
        this.child = child; timer = setTimeout(unavailable, this.timeoutMs);
        child.once('message', result => result?.ok ? finish({status: 'ready', ...result.data, updated_at: new Date(this.now()).toISOString()}) : unavailable());
        child.once('error', unavailable); child.once('exit', unavailable);
        child.send({...target, section, id});
      } catch {unavailable();}
    });
  }
}
module.exports = {DiscoveryManager};
