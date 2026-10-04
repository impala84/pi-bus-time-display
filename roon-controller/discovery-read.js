'use strict';
const model = require('./discovery-model');
const namespace = 'Sooloos.Broker.Api';
async function dailyPicks(client, sdk, time) {
  const {BinaryWriter, Arg, buildArgs} = sdk;
  const type = `${namespace}.DailyPicksParameters`;
  const fields = [{name: `string ${type}::LocalTime`, propType: 20, value: new BinaryWriter().string(time).toBuffer()},
    ...['OverrideCache', 'RecentlyAddedOnly', 'NewReleasesOnly'].map(name => ({name: `bool ${type}::${name}`, propType: 2, value: buildArgs([Arg.bool(false)])}))];
  const args = buildArgs([Arg.sooid(client.profile())]);
  const current = await client.remoting.callMethod(client.serviceOid('Library'),
    `${namespace}.Library::GetDailyPicks(System.Sooid, ${type}, Base.ResultCallback<${namespace}.DataList<${namespace}.DailyPicksBox>>)`,
    Buffer.concat([args, client.structArg(type, fields)]));
  if (current.status !== 'MissingMethod') return current;
  // Older server signature remains supported; no brute-force signature loop.
  return client.remoting.callMethod(client.serviceOid('Library'),
    `${namespace}.Library::GetDailyPicks(System.Sooid, string, bool, Base.ResultCallback<${namespace}.DataList<${namespace}.DailyPicksBox>>)`,
    Buffer.concat([args, buildArgs([Arg.str(time), Arg.bool(false)])]));
}
async function readDiscovery(client, sdk, section, id) {
  const {Arg, buildArgs, exportPlayHistory} = sdk;
  const call = (method, args, result) => client.remoting.callMethod(client.serviceOid('Library'), `${namespace}.Library::${method}(System.Sooid, ${result})`, args);
  let result;
  if (section === 'recent') {
    const history = await exportPlayHistory(client, {limit: 100, pageSize: 50, timeoutMs: 5000});
    return {items: model.recentAlbums(client.graph, history.events)};
  }
  if (section === 'daily') {
    result = await dailyPicks(client, sdk, new Date().toISOString());
    if (!result.success) throw new Error('Personalised recommendations are unavailable in this Roon version');
    const root = client.graph.decodeReturnValue(Uint8Array.from(result.payload));
    await new Promise(resolve => setTimeout(resolve, 1000));
    const groups = model.picks(client.graph, root);
    result = await client.remoting.callMethod(client.serviceOid('Library'),
      `${namespace}.Library::GetMixes(System.Sooid, string, Base.ResultCallback<${namespace}.DataList<${namespace}.Mix>>)`,
      buildArgs([Arg.sooid(client.profile()), Arg.str(new Date().toISOString())]));
    if (!result.success) throw new Error('Daily mixes are unavailable in this Roon version');
    const mixRoot = client.graph.decodeReturnValue(Uint8Array.from(result.payload));
    await new Promise(resolve => setTimeout(resolve, 1000));
    return {items: model.mixes(client.graph, mixRoot), groups};
  }
  if (section === 'mix') {
    if (!/^[a-f0-9]{2,160}$/i.test(id || '') || id.length % 2) throw new Error('Invalid mix reference');
    result = call('GetMix', buildArgs([Arg.sooid(Buffer.from(id, 'hex'))]), `Base.ResultCallback<${namespace}.Mix>`);
    result = await result;
    if (!result.success) throw new Error('This mix is no longer available');
    const root = client.graph.decodeReturnValue(Uint8Array.from(result.payload));
    if (!root?.$ref) throw new Error('Invalid mix result');
    result = await client.remoting.callMethod(BigInt(root.$ref), `${namespace}.Mix::GetItems(Base.ResultCallback<${namespace}.DataList<${namespace}.MixItem>>)`, Buffer.alloc(0));
    if (!result.success) throw new Error('The mix track list could not be loaded');
    const tracks = client.graph.decodeReturnValue(Uint8Array.from(result.payload));
    await new Promise(resolve => setTimeout(resolve, 1000));
    return {mix: model.mixes(client.graph, {$items:[root]}, 1)[0] || null, items: model.list(client.graph, tracks, 20).flatMap(group => model.list(client.graph, model.field(group, 'Tracks'), 5).map(track => model.item(client.graph, track, 'track'))).filter(Boolean), total: Number(model.field(model.resolve(client.graph, tracks), '$count') || 0)};
  }
  if (section !== 'releases') throw new Error('Unknown Discover section');
  result = await call('GetNewReleasesForYou', buildArgs([Arg.sooid(client.profile())]), `Base.ResultCallback<${namespace}.DataList<${namespace}.AlbumWithExtras>>`);
  if (!result.success) throw new Error('New Releases are unavailable in this Roon version');
  const root = client.graph.decodeReturnValue(Uint8Array.from(result.payload));
  await new Promise(resolve => setTimeout(resolve, 1000));
  return {items: model.list(client.graph, root, 20).map(wrapper => model.item(client.graph, model.field(wrapper, 'Album'))).filter(Boolean)};
}
module.exports = {dailyPicks, readDiscovery};
