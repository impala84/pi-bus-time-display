'use strict';

const PAGE_SIZE = 30;

function request(service, method, options) {
  return new Promise((resolve, reject) => service[method](options, (error, result) => error ? reject(new Error(String(error))) : resolve(result || {})));
}

function safeSession(value) {
  const clean = String(value || 'web').replace(/[^a-zA-Z0-9_-]/g, '').slice(0, 48);
  return `pihome-${clean || 'web'}`;
}

function publicItem(item) {
  return {
    title: String(item?.title || ''), subtitle: String(item?.subtitle || ''),
    image_key: item?.image_key || null, item_key: item?.item_key || null,
    hint: item?.hint || null, input_prompt: item?.input_prompt ? {
      prompt: String(item.input_prompt.prompt || 'Search'), action: String(item.input_prompt.action || 'Go'),
      value: String(item.input_prompt.value || ''), is_password: Boolean(item.input_prompt.is_password)
    } : null
  };
}

function browserLayout(hierarchy, level, list, items) {
  const title = String(list?.title || '');
  const subtitle = String(list?.subtitle || '');
  if (hierarchy === 'browse' && Number(level || 0) === 0) return {layout: 'home', show_labels: true};
  const usable = items.filter(item => item.hint !== 'header');
  if (/^library$/i.test(title)) return {layout: 'menu', show_labels: true};
  if (/playlists?/i.test(title) || (/\btracks?\b/i.test(subtitle) && !/^tracks?$/i.test(title))) return {layout: 'list', show_labels: true};
  const imageRatio = usable.length ? usable.filter(item => item.image_key).length / usable.length : 0;
  if (imageRatio >= .45) return {layout: 'covers', show_labels: !/albums?/i.test(title)};
  if (usable.length > 0 && usable.length <= 10 && !usable.some(item => item.hint === 'action')) return {layout: 'menu', show_labels: true};
  return {layout: 'list', show_labels: true};
}

function libraryItems(list, items) {
  if (!/^library$/i.test(String(list?.title || '').trim())) return items;
  return items.filter(item => !/^(search|tags?)$/i.test(String(item.title || '').trim()));
}

function withFallbackImage(items, imageKey) {
  if (!imageKey) return items;
  return items.map(item => item.hint !== 'action' && !item.image_key ? {...item, image_key: imageKey} : item);
}

function rootItems(items) {
  const wanted = ['library', 'playlists', 'genres', 'tidal'];
  const available = items.filter(item => item.hint !== 'header');
  const selected = wanted.map(name => available.find(item => String(item.title || '').trim().toLowerCase() === name)).filter(Boolean);
  for (const item of available) {
    if (selected.length >= 4) break;
    if (!selected.includes(item)) selected.push(item);
  }
  return selected;
}

class BrowseManager {
  constructor(service, zone) {
    this.service = service;
    this.zone = zone;
    this.sessions = new Map();
    this.pending = new Map();
  }

  clear() { this.sessions.clear(); this.pending.clear(); }

  run(sessionName, command = 'current', data = {}) {
    const session = safeSession(sessionName);
    const previous = this.pending.get(session) || Promise.resolve();
    const current = previous.catch(() => {}).then(() => this._run(session, command, data));
    this.pending.set(session, current);
    return current.finally(() => { if (this.pending.get(session) === current) this.pending.delete(session); });
  }

  async _run(session, command, data) {
    const service = this.service(); const zone = this.zone();
    if (!service || !zone) return {status: 'unavailable', title: 'Browse', items: [], can_back: false, has_more: false};
    if (command === 'current' && this.sessions.has(session)) return this.sessions.get(session);
    if (command === 'more') return this.loadMore(service, session);
    if (command === 'search') return this.search(service, zone, session, String(data.query || '').trim());
    const state = this.sessions.get(session);
    if (command === 'back' && state?.hierarchy !== 'browse' && state?.level === 0) return this._run(session, 'root', {});
    const hierarchy = command === 'root' || !state ? 'browse' : state.hierarchy;
    const options = {hierarchy, multi_session_key: session, zone_or_output_id: zone.zone_id};
    if (command === 'root' || !state) options.pop_all = true;
    else if (command === 'back') options.pop_levels = 1;
    else if (command === 'open' && data.item_key) options.item_key = String(data.item_key);
    else return state || this._run(session, 'root', {});
    const opened = command === 'open' ? state?.items?.find(item => String(item.item_key) === String(data.item_key)) : null;
    return this.follow(service, session, hierarchy, await request(service, 'browse', options), opened?.image_key || null);
  }

  async search(service, zone, session, query) {
    if (!query) return this._run(session, 'root', {});
    const options = {hierarchy: 'search', multi_session_key: session, zone_or_output_id: zone.zone_id, pop_all: true};
    const root = await request(service, 'browse', options);
    const initial = await request(service, 'load', {hierarchy: 'search', multi_session_key: session, level: root.list?.level, offset: 0, count: 30});
    const prompt = (initial.items || []).find(item => item.input_prompt && item.item_key);
    if (!prompt) return this.store(session, 'search', root.list || initial.list, initial.items || [], `No search input is available for “${query}”.`);
    const result = await request(service, 'browse', {hierarchy: 'search', multi_session_key: session, zone_or_output_id: zone.zone_id, item_key: prompt.item_key, input: query});
    return this.follow(service, session, 'search', result);
  }

  async follow(service, session, hierarchy, result, fallbackImageKey = null) {
    if (result.action === 'message') {
      const state = this.sessions.get(session) || {status: 'ready', hierarchy, title: 'Browse', items: [], can_back: false, has_more: false};
      return this.save(session, {...state, message: String(result.message || (result.is_error ? 'Roon could not complete that action.' : 'Done.')), error: Boolean(result.is_error)});
    }
    if (result.action !== 'list' || !result.list) {
      const state = this.sessions.get(session) || {status: 'ready', hierarchy, title: 'Browse', items: [], can_back: false, has_more: false};
      return this.save(session, {...state, message: 'Done.', error: false});
    }
    const loaded = await request(service, 'load', {hierarchy, multi_session_key: session, level: result.list.level, offset: 0, count: PAGE_SIZE});
    return this.store(session, hierarchy, loaded.list || result.list, loaded.items || [], '', fallbackImageKey);
  }

  store(session, hierarchy, list, items, message, fallbackImageKey = null) {
    const level = Number(list?.level || 0);
    let normalised = withFallbackImage(libraryItems(list, (items || []).map(publicItem)), fallbackImageKey);
    if (hierarchy === 'browse' && level === 0) normalised = rootItems(normalised);
    const presentation = browserLayout(hierarchy, level, list, normalised);
    const filteredLibrary = /^library$/i.test(String(list?.title || '').trim());
    const count = filteredLibrary ? normalised.length : Number(list?.count ?? normalised.length);
    return this.save(session, {
      status: 'ready', hierarchy, level, title: presentation.layout === 'home' ? 'Browse' : String(list?.title || (hierarchy === 'search' ? 'Search' : 'Browse')),
      subtitle: String(list?.subtitle || ''), count, offset: Number(list?.display_offset || 0),
      items: normalised, can_back: hierarchy !== 'browse' || Number(list?.level || 0) > 0,
      has_more: !filteredLibrary && presentation.layout !== 'home' && normalised.length < count, fallback_image_key: fallbackImageKey, message, error: false,
      ...presentation
    });
  }

  async loadMore(service, session) {
    const state = this.sessions.get(session);
    if (!state || !state.has_more) return state || this._run(session, 'root', {});
    const loaded = await request(service, 'load', {hierarchy: state.hierarchy, multi_session_key: session, level: state.level, offset: state.items.length, count: PAGE_SIZE});
    const items = [...state.items, ...withFallbackImage((loaded.items || []).map(publicItem), state.fallback_image_key)];
    return this.save(session, {...state, items, count: Number(loaded.list?.count ?? state.count), has_more: items.length < Number(loaded.list?.count ?? state.count), message: ''});
  }

  save(session, state) { this.sessions.set(session, state); return state; }
}

module.exports = {BrowseManager, browserLayout, libraryItems, publicItem, rootItems, safeSession, withFallbackImage};
