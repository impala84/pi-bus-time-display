#!/usr/bin/env node
'use strict';

// Deliberately not imported by the production controller. A bounded, manual,
// read-only feasibility run against a Core the operator owns. No mutations,
// playback, automatic reconnects or persistent raw graph dumps.
const path = require('node:path');
const {setTimeout: delay} = require('node:timers/promises');
const {referencePreview} = require('./discovery-wire.cjs');
const model = require('../roon-controller/discovery-model');

async function main() {
  const host = process.env.ROON_HOST;
  const broker = process.env.ROON_SERVER_BROKER_ID;
  const clientPath = process.env.ROON_RESEARCH_CLIENT;
  if (!host || !clientPath || !/^[a-f0-9]{32}$/i.test(broker || '')) {
    throw new Error('Set ROON_HOST, ROON_SERVER_BROKER_ID (wire-order hex), and ROON_RESEARCH_CLIENT (built upstream dist directory)');
  }
  const {RoonClient, makeApi, BinaryWriter, Arg, buildArgs, generated} = require(path.resolve(clientPath));
  const {exportPlayHistory} = require(path.join(path.resolve(clientPath), 'history-export.js'));
  const client = new RoonClient({host, serverBrokerId: Buffer.from(broker, 'hex')});
  const watchdog = setTimeout(() => {
    client.close();
    console.error('Discovery proof exceeded its 90-second limit; stopped without retry.');
    process.exit(2);
  }, 90000);
  const report = {experimental: true, playbackVerified: false, results: {}};
  const roots = new Map();
  const serialise = value => JSON.stringify(value, (_, v) => typeof v === 'bigint' ? v.toString() : v);
  try {
    await client.connect();
    const api = makeApi(client);
    // Resolve only objects reachable from this call's returned root. Never
    // infer list membership from unrelated objects already in the graph.
    function inspect(root) {
      const seen = new Set(), entries = [];
      const inline = (v, depth = 0) => {
        if (depth > 4) return '[bounded]';
        if (Buffer.isBuffer(v)) return {opaqueHex: v.toString('hex')};
        if (v === null || typeof v !== 'object') return v;
        if ('$ref' in v) return v;
        if (Array.isArray(v)) return v.slice(0, 5).map(x => inline(x, depth + 1));
        return Object.fromEntries(Object.entries(v).slice(0, 30).map(([k, x]) => [k, inline(x, depth + 1)]));
      };
      const walk = (value, depth = 0) => {
        if (depth > 8 || seen.size > 200 || value == null) return;
        if (Array.isArray(value)) {value.slice(0, 5).forEach(v => walk(v, depth + 1)); return;}
        if (typeof value !== 'object' || Buffer.isBuffer(value)) return;
        if ('$ref' in value) {
          const key = String(value.$ref);
          if (seen.has(key)) return;
          seen.add(key);
          const object = client.graph.getObject(BigInt(key));
          if (!object) {entries.push({unresolved: true}); return;}
          if (!/\.(DataList<|PartialList<|Album|Track|Performer|Mix|Playlist|Image)/.test(object.typeName)) return;
          const fields = {};
          for (const [name, v] of Object.entries(object.fields)) {
            const short = name.split('::').pop();
            if (!/localized|sortkey|filterkey/i.test(short) && (/title|name|perform|artist|album|track|description|reason|context|source|avail|image|cover|id$|count/i.test(short) || /\.(Mix|Image)$/.test(object.typeName))) {
              if (Buffer.isBuffer(v)) fields[short] = {opaqueHex: v.toString('hex')};
              else fields[short] = inline(v);
            }
          }
          entries.push({type: object.typeName, fields, ...(/\.Mix$/.test(object.typeName) ? {fieldNames: Object.keys(object.fields)} : {})});
          for (const [name, v] of Object.entries(object.fields)) {
            if (name === '$items' || /::(Album|Albums|Track|Tracks|Image|Images|Items|MainPerformers|Performers|PerformerMixDescription|GenreMixDescription|SampleArtistNames)$/.test(name)) walk(v, depth + 1);
          }
        } else {
          if (value.$type?.endsWith('.DailyPicksBox')) entries.push({type: value.$type, fields: inline(value)});
          for (const [name, v] of Object.entries(value)) {
          if (/::Items$/.test(name) && Buffer.isBuffer(v)) referencePreview(v).forEach(ref => walk(ref, depth + 1));
          else if (name === '$items' || /::(Album|Albums|Track|Tracks|Performers|SeedAlbum|SeedPerformer|Image|Images|Items|MainPerformers|Avatar|Photo|Touchstones)$/.test(name)) walk(v, depth + 1);
          }
        }
      };
      walk(root);
      return {objects: entries, bounded: true};
    }
    async function capture(name, action) {
      try {
        const result = await action();
        if (!result.success) throw new Error(`Server returned ${result.status}`);
        const root = client.graph.decodeReturnValue(Uint8Array.from(result.payload));
        roots.set(name, root);
        await delay(1500);
        report.results[name] = {status: 'received', ...inspect(root)};
      } catch (error) {report.results[name] = {status: 'unavailable', error: error.message};}
      console.log(serialise({section: name, ...report.results[name]}));
    }
    await capture('dailyMixes', () => api.tidal.getDailyMixes(0, 5));
    await capture('dailyPicks', () => api.library.getDailyPicks(client.profile(), new Date().toISOString(), false));
    if (report.results.dailyPicks.status === 'unavailable') {
      // Current installed Roon.Broker.Api.dll has a parameters struct rather
      // than the older (profile, time, overrideCache) signature. These four
      // fields were read from that assembly, not guessed from method names.
      const type = 'Sooloos.Broker.Api.DailyPicksParameters';
      const fields = [
        {name: `string ${type}::LocalTime`, propType: 20, value: new BinaryWriter().string(new Date().toISOString()).toBuffer()},
        ...['OverrideCache', 'RecentlyAddedOnly', 'NewReleasesOnly'].map(name => ({name: `bool ${type}::${name}`, propType: 2, value: buildArgs([Arg.bool(false)])})),
      ];
      await capture('currentDailyPicks', () => client.remoting.callMethod(client.serviceOid('Library'),
        `Sooloos.Broker.Api.Library::GetDailyPicks(System.Sooid, ${type}, Base.ResultCallback<Sooloos.Broker.Api.DataList<Sooloos.Broker.Api.DailyPicksBox>>)`,
        Buffer.concat([buildArgs([Arg.sooid(client.profile())]), client.structArg(type, fields)])));
    }
    await capture('roonMixes', () => api.library.getMixes_3(client.profile(), new Date().toISOString()));
    const firstMix = client.graph.findByType('Mix')[0];
    const mixId = Object.entries(firstMix?.fields || {}).find(([key]) => key.endsWith('::MixId'))?.[1];
    if (Buffer.isBuffer(mixId)) await capture('mixDetail', () => api.library.getMix(mixId));
    if (firstMix) await capture('mixTracks', () => new generated.MixApi(client, firstMix.oid).getItems());
    console.log(serialise({section: 'normalisedMixes', items: model.mixes(client.graph, roots.get('roonMixes')).map(({artwork, ...mix}) => ({...mix, artwork_available: Boolean(artwork.url || artwork.id)}))}));
    console.log(serialise({section: 'normalisedPicks', groups: model.picks(client.graph, roots.get('currentDailyPicks') || roots.get('dailyPicks')).map(group => ({reason: group.reason, category: group.category, seed: group.seed?.title, items: group.items.map(({title, artist}) => ({title, artist}))}))}));
    console.log(serialise({section: 'normalisedMixTracks', tracks: model.list(client.graph, roots.get('mixTracks')).flatMap(group => model.list(client.graph, model.field(group, 'Tracks')).map(track => model.item(client.graph, track, 'track'))).filter(Boolean)}));
    console.log(JSON.stringify({section:'capabilities', fields:Object.fromEntries(Object.entries(client.graph.findByType('Library')[0]?.fields||{}).filter(([key,value])=>/Supports.*(Daily|Mix)|Version/.test(key)&&typeof value!=='object'))}));
    await capture('newReleases', () => api.library.getNewReleasesForYou(client.profile()));
    try {
      report.results.recent = {status: 'received', ...await exportPlayHistory(client, {limit: 5, pageSize: 5, timeoutMs: 5000})};
    } catch (error) {report.results.recent = {status: 'unavailable', error: error.message};}
    console.log(serialise({section: 'recent', ...report.results.recent}));
    const ready = (report.results.currentDailyPicks?.objects || report.results.dailyPicks?.objects)?.some(o => o.type?.endsWith('.DailyPicksBox')) && report.results.roonMixes?.objects?.some(o => o.fields?.PerformerMixDescription) && report.results.newReleases?.objects?.some(o => o.fields?.Title) && report.results.recent?.events?.length > 0;
    console.log(serialise({completed: true, dataGatePassed: Boolean(ready), uiGatePassed: false, playbackVerified: false}));
    // Receiving some data is not success for the complete requested scope.
    if (!ready) process.exitCode = 3;
  } finally {clearTimeout(watchdog); client.close();}
}

main().catch(error => {console.error(error.message); process.exitCode = 1;});
